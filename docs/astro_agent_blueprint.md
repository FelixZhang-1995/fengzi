# 北京天文馆科普大模型技术蓝图

本文件在先前总体方案基础上，进一步给出可执行的代码框架、数据 Schema、训练脚本示例、RAG 路由设计，以及传感器与视觉处理落地方案。示例使用 Python/Unix 风格，便于在本地或边缘设备快速搭建原型。

## 1. 目录结构建议
```
project/
├── data_pipeline/          # OCR/ASR/抽帧/清洗脚本
├── rag/                    # 检索与路由
├── models/                 # SFT/LoRA/量化
├── services/               # 推理与编排微服务
├── web/                    # 前端或触摸屏/投影 H5
├── configs/
│   ├── datasources.yaml    # 数据源与采集计划
│   ├── rag.yaml            # 检索路由、索引分区
│   └── personas.yaml       # 展区/人设模板
├── eval/                   # 评测脚本与基准
└── docs/                   # 技术文档
```

## 2. 数据 Schema（示例）
### 2.1 文本/FAQ/讲解词
```yaml
# data_schema/text.yaml
- id: astro-00123
  title: "太阳系展厅-日冕大喷发"
  type: "script"          # script|faq|article|news
  persona: "solar_guide"
  audience: "teen"        # kid|teen|adult
  lang: "zh"
  body: |
    ...讲解全文...
  source:
    origin: "北京天文馆"
    license: "internal"
    timestamp: "2024-08-01"
```

### 2.2 多模态元数据（图/视频/音频）
```json
{
  "id": "img-planet-0001",
  "modality": "image",
  "path": "s3://astro/images/planet.jpg",
  "caption": "展品：类木行星模型，位于太阳系展区入口右侧",
  "embedding_model": "clip-ViT-L/14",
  "bbox": [120, 34, 420, 380],
  "tags": ["木星", "展品照片", "太阳系展区"],
  "source": {"origin": "馆内拍摄", "license": "internal", "timestamp": "2024-07-12"}
}
```

### 2.3 结构化知识图谱节点（简化）
```json
{
  "node_id": "object:jupiter",
  "label": "木星",
  "type": "planet",
  "aliases": ["Jupiter"],
  "facts": {
    "mass": "1.898e27 kg",
    "radius": "69911 km",
    "orbital_period": "4332.59 days"
  },
  "relations": [
    {"predicate": "orbits", "object": "sun"},
    {"predicate": "has_mission", "object": "mission:juno"}
  ],
  "source": "IAU/NASA"
}
```

## 3. 采集与预处理流水线
- **OCR**：PaddleOCR/DocTR；输出带版面坐标 JSON。脚本示例 `data_pipeline/ocr.py` 调用批处理。
- **视频抽帧**：每 N 秒/镜头变化抽关键帧 + Whisper 提取字幕。
- **ASR**：Whisper/Paraformer → 文本；自动段落分割。
- **清洗**：去重、敏感词过滤、数字/天体名称校对（术语表）。
- **切分**：文档按语义块（200-512 tokens）分片并保留来源 ID；图像可用 CLIP 划分特征。

示例：批量 OCR 和入库
```python
# data_pipeline/ocr.py
from pathlib import Path
from paddleocr import PaddleOCR
import json

ocr = PaddleOCR(use_angle_cls=True, lang="ch")

def process_pdf(pdf_path: Path, out_dir: Path):
    pages = ocr.ocr(str(pdf_path), cls=True)
    records = []
    for i, page in enumerate(pages):
        for line, (bbox, (text, prob)) in enumerate(page):
            records.append({
                "page": i,
                "line": line,
                "text": text,
                "prob": prob,
                "bbox": bbox,
                "source_file": pdf_path.name,
            })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pdf_path.stem}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
```

## 4. RAG 检索路由设计
- **索引分片**：按展区/专题（如 solar, deep_space, history, kids）建立命名空间；文本向量 + 图片向量 + 结构化 KV。
- **路由逻辑**（伪代码）
```python
# rag/router.py
from typing import Dict

def route(query: str, metadata: Dict) -> Dict:
    intent = detect_intent(query)            # faq | script | news | fact_check | nav
    persona = metadata.get("persona", "default")
    if intent == "nav":
        return {"namespace": "map", "topk": 5, "rerank": True}
    if "图片" in query or metadata.get("has_image"):
        return {"namespace": f"{persona}:vision", "modalities": ["image", "text"], "topk": 8}
    return {"namespace": persona, "topk": 8, "rerank": True}
```
- **检索执行**：
  - 文本：`embedding = bge-m3` / `gte-Qwen2`；向量库 Milvus/PGVector。
  - 图片：CLIP/EVACLIP；可选多模态向量库（如 Milvus multimodal 或单独存储）。
  - Rerank：bge-reranker-v2 或 cross-encoder；对长文用 Hybrid（BM25 + 向量）。
- **响应模板**：回答中注明来源与时间，缺少证据时给出“未检索到权威来源”。

## 5. 微调与持续学习
### 5.1 指令微调样例
```bash
# models/run_sft.sh
CUDA_VISIBLE_DEVICES=0,1 torchrun --nproc_per_node=2 train_sft.py \
  --model_name_or_path Qwen2-7B \
  --data_path data/sft/astro_qa.jsonl \
  --per_device_train_batch_size 4 \
  --learning_rate 1e-5 \
  --max_seq_length 2048 \
  --num_train_epochs 3 \
  --gradient_accumulation_steps 4 \
  --bf16 True \
  --logging_steps 10 \
  --save_steps 500 \
  --output_dir outputs/qwen2-astro-sft
```

### 5.2 LoRA/PEFT（节省显存）
```python
# models/train_sft.py 片段
from peft import LoraConfig, get_peft_model

config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], lora_dropout=0.05)
model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16)
model = get_peft_model(model, config)
```

### 5.3 量化部署
- 推理时用 `bitsandbytes` INT4 或 `AWQ/GPTQ`；KV cache + streaming 响应；多进程多路并发。
- `text-generation-inference` 或 `vLLM` 部署，附加检索插件。

### 5.4 持续学习
- 新展览上线：新增文档 → 更新 RAG 索引；小规模增量 SFT 数据（<5k 样本）→ 继续训练或使用 Adapter merge。
- 定期蒸馏：将大模型回答蒸馏到轻量版边缘模型（如 3B-7B）。

## 6. 多模态与传感器
- **视觉**：
  - 展厅摄像头/机器人视觉 → 实时拍摄 → CLIP/Detector（YOLOv8/RT-DETR）识别展品或人流密度。
  - 用户上传图片：调用图文 VLM (Qwen2-VL/InternVL) → 结合 RAG 注释展品信息。
- **视频**：抽帧 + ASR 字幕 + 动态摘要；对长视频可生成分段讲解提纲。
- **语音**：ASR → LLM；回答经 TTS（CosyVoice/FishSpeech）输出；机器人动作同步由编排层发送。
- **传感器**：
  - 气象/星象 API：获取当日可观测目标、北京能见度、日落时间，填充讲解。
  - 馆内传感器：红外/人流计数器 → 动态调整讲解节奏、推荐人少展区。
  - 交互设备：触摸屏/投影/机器人 SDK 提供统一接口，如 `/services/device_adapter.py`。

示例：气象与星历工具调用
```python
# services/tools/astro_tools.py
import requests

def get_beijing_weather(api_key: str):
    resp = requests.get(f"https://api.qweather.com/v7/weather/now?location=101010100&key={api_key}")
    data = resp.json()
    return {
        "temp": data["now"]["temp"],
        "text": data["now"]["text"],
        "wind": data["now"]["windDir"]
    }

def next_meteor_shower(api_url: str):
    resp = requests.get(api_url).json()
    return resp.get("next_event", {})
```

## 7. 服务编排示例
```python
# services/orchestrator.py
from rag.router import route
from rag.search import search
from services.tools.astro_tools import get_beijing_weather
from llm import chat

async def handle_query(query, metadata):
    plan = route(query, metadata)
    contexts = search(query, plan)
    answer = await chat(prompt=build_prompt(query, contexts, metadata))
    if "天气" in query:
        weather = get_beijing_weather(api_key=metadata["weather_key"])
        answer += f"\n当前北京天气：{weather['text']}，{weather['temp']}°C，风向{weather['wind']}。"
    return answer
```

## 8. 评测与安全
- **评测集**：馆内 FAQ、常见误区、更正语料、儿童模式易懂度、多轮导览任务。
- **指标**：事实性（自动检索对齐 + 人审）、风格一致、Persona 匹配、延迟、ASR/TTS 质量。
- **安全策略**：涉政/暴力/谣言过滤；缺乏来源时提示“建议参考官方资料”；对外部新闻加时间戳声明。

## 9. 部署形态
- **边缘一体机**：GPU + 本地索引；断网可用；定期离线同步。
- **云边协同**：云端重建索引/训练，夜间同步；前台实时走本地推理。
- **监控**：Prometheus + Grafana；日志脱敏；异常回答留样复检。

## 10. 快速原型步骤
1. 用上述 `data_pipeline/ocr.py` 和抽帧脚本采集首批馆内资料。
2. 构建 `rag.yaml` 命名空间，跑通向量检索 + rerank。
3. 选 Qwen2-7B + LoRA SFT，微调 2-3 epoch，验证 FAQ/讲解脚本一致性。
4. 前端用简单 Web/Touch UI 对接 `services/orchestrator.py`，接入 ASR/TTS。
5. 逐步加入视觉识别、星历工具、机器人动作接口，扩大多模态覆盖。

## 11. Mac Studio M2 Ultra 从 0 开始上手步骤（小白友好）
以下步骤假设你是第一次搭建环境，并希望在 1-4 台 Mac Studio M2 Ultra 上快速跑通最小可用版本。

### 11.1 基础工具安装（只做一次）
1. 打开“终端”执行安装 Homebrew（包管理器）：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   为什么：后续所有依赖（Git、Python 工具、FFmpeg 等）都能用 brew 一键安装。
2. 安装 Git、FFmpeg、wget（下载、解压、处理音视频）：
   ```bash
   brew install git ffmpeg wget
   ```
3. 安装 Miniforge（Conda 发行版，方便独立 Python 环境）：
   ```bash
   brew install --cask miniforge
   ```
   安装后在终端中执行 `conda init zsh`，重新打开终端即可使用 `conda` 命令。

### 11.2 克隆代码与创建隔离环境
```bash
git clone <你的代码仓库地址> astro-agent
cd astro-agent

# 创建独立环境，避免污染系统 Python
conda create -n astro python=3.11 -y
conda activate astro

# 安装 PyTorch（苹果芯片用 Metal 加速）、常用依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt  # 若仓库后续补充此文件
pip install paddleocr pillow pydantic langchain llama-index milvus-lite openai tiktoken
```
概念解释：
- **隔离环境**：像“虚拟房间”，把项目依赖与系统隔离，方便升级或删除而不影响别的项目。
- **Metal 加速**：苹果芯片上的图形/AI 加速接口，让 PyTorch 在 Mac 上跑得更快。

### 11.3 准备首批数据与示例运行
1. 创建数据目录，放入任意 PDF（展品说明书等）与一张展品图片：
   ```bash
   mkdir -p data/raw_pdf data/raw_img outputs
   cp ~/Downloads/sample.pdf data/raw_pdf/
   cp ~/Downloads/exhibit.jpg data/raw_img/
   ```
2. 运行 OCR 示例，得到 JSON 结果：
   ```bash
   python data_pipeline/ocr.py data/raw_pdf/sample.pdf outputs/ocr_json
   ```
3. 对图片生成向量嵌入（示例，需在 `rag/` 中准备脚本）：
   ```bash
   python rag/embed_image.py --image data/raw_img/exhibit.jpg --out outputs/exhibit.npy
   ```
4. 启动一个最小检索 + 对话样例（可用 LangChain/LlamaIndex Quickstart）：
   ```bash
   python services/orchestrator.py --demo_query "这件展品的故事是什么？"
   ```
   如果首次没有模型，可先接入线上 API（如 OpenAI/Qwen API），后续再换成本地模型。

### 11.4 本地大模型运行（可选，能力更强）
1. 下载轻量模型（示例用 Qwen2-1.5B-Instruct）并做一次最小指令微调：
   ```bash
   mkdir -p models/base
   wget -O models/base/qwen2-1_5b.safetensors <模型下载链接>
   ```
2. 运行示例微调脚本（占用小，适合单机测试）：
   ```bash
   bash models/run_sft.sh
   ```
3. 验证推理：
   ```bash
   python llm/chat_demo.py --model outputs/qwen2-astro-sft --prompt "请用儿童口吻介绍木星"
   ```
注意：M2 Ultra 适合跑 7B 以内模型流畅测试；更大模型可用 4-bit 量化或多机并行。

### 11.5 多机协同（1-4 台设备）
- **参数服务器思路**：一台机器做“索引与路由”（Milvus/PGVector + RAG），其余机器做推理服务（vLLM/TGI）。
- **文件同步**：用 `rsync` 或 `git pull` 同步数据/代码；定期在“主机”重建向量索引后分发。
- **监控**：在其中一台机器部署 Prometheus + Grafana，拉取各机器的延迟、GPU/CPU 占用指标。

### 11.6 典型问题排查
- 运行命令显示“权限不足”：在命令前加 `sudo` 或检查目标目录是否可写。
- 安装包太慢：配置国内镜像，如 `pip config set global.index-url https://mirrors.aliyun.com/pypi/simple`。
- 模型显存不足：降低 batch size、启用 LoRA/4-bit 量化，或改用更小的基座模型。

## 12. 天文科普展览的 AI 应用扩展与研究路径
下列方向可逐步纳入产品或研究规划，每个都附带“需要打通的路径”，便于落地：

1. **沉浸式多屏/球幕联动讲解**
   - 价值：在球幕、穹顶、投影墙同步播报图像与讲解，提供沉浸体验。
   - 路径：
     - 数据：高分辨率天体可视化素材、三维轨道模型（SPICE 数据）。
     - 模型/算法：时间轴驱动的脚本生成 + 画面事件触发；延时校准。
     - 部署：播放器控制接口（OSC/DMX/局域网指令），与讲解文本/语音同步。

2. **观众画像与个性化科普**
   - 价值：根据年龄/兴趣/停留时间推送不同深度与互动问题。
   - 路径：
     - 数据：入口问卷、互动日志、展区停留时长（匿名聚合）。
     - 模型：意图识别 + Persona 路由；少量 SFT 让模型学会“分层讲解”。
     - 部署：前端调用时附带用户画像标签，RAG 路由选择对应命名空间与语气。

3. **实时天象播报与观测助手**
   - 价值：自动解读当天可见行星、流星雨、日食月食等，结合天气/能见度给出观测建议。
   - 路径：
     - 数据：星历 API（JPL Horizons/Minor Planet Center）、气象 API、馆内观测日志。
     - 模型：工具调用链（weather + ephemeris），生成“今晚观测清单”。
     - 部署：定时任务刷新结果，推送到触摸屏/公众号/语音播报。

4. **展品识别 + 讲解跳转**
   - 价值：观众用手机或触摸屏拍摄展品，系统自动识别并播放对应讲解。
   - 路径：
     - 数据：馆内展品多角度照片、标注展品 ID。
     - 模型：YOLO/RT-DETR 检测 + CLIP 识别；RAG 拉取展品 FAQ/脚本。
     - 部署：前端上传图片 → VLM/识别 → 触发对应讲解脚本。

5. **互动问答闯关/学习路径推荐**
   - 价值：把展览变成“任务树”，完成答题解锁下一展品，提升参与度。
   - 路径：
     - 数据：按展区设计关卡题库、错误示例与标准解释。
     - 模型：生成解释 + 自动评分（对比标准答案/关键词匹配）；保存成绩与路线。
     - 部署：前端展示进度条；后端记录通关状态，动态推荐下一个展品。

6. **谣言纠错与时效性新闻解读**
   - 价值：快速回应“地平说”“占星”等谣言，或对突发太空新闻给出科普解读。
   - 路径：
     - 数据：谣言对照表、权威来源链接、新闻 RSS/官方稿件。
     - 模型：RAG + 事实核查模板；回答附带时间戳与来源。
     - 部署：后台定时拉取新闻，自动生成“今日科普看点”卡片。

7. **无障碍与多语言科普**
   - 价值：面向听障/视障/外语游客，提供字幕、手语视频、实时翻译。
   - 路径：
     - 数据：多语言讲解词、手语视频素材；对照文本。
     - 模型：ASR + TTS 多语言；文本翻译模型；手语生成可用姿态驱动合成（研究中）。
     - 部署：在播放器层增加字幕轨道与语言切换按钮。

8. **观众流量预测与馆内调度**
   - 价值：提前预测高峰，动态调整讲解频率与路线推荐。
   - 路径：
     - 数据：历史客流、节假日标签、天气；实时传感器计数。
     - 模型：时间序列预测（Prophet/LSTM） + 规则警报。
     - 部署：后台仪表板 + 提前推送“错峰参观”建议。

9. **科学实验/课堂自动生成教案**
   - 价值：为研学团体自动生成课程提纲、实验步骤、材料清单。
   - 路径：
     - 数据：现有课程教案、实验记录、教材片段。
     - 模型：SFT 让模型学会输出“目标-材料-步骤-安全提示”格式；内容安全校验。
     - 部署：教师在后台输入主题 → 系统生成可打印/投影的教案 PDF。

10. **可解释的知识图谱导航**
    - 价值：从“太阳系→木星→探测任务”形成可视化知识路径，辅助讲解。
    - 路径：
      - 数据：结构化节点与关系（见 §2.3）。
      - 模型：图谱检索 + LLM 生成解释；可视化库（ECharts/D3）。
      - 部署：触摸屏点击节点可展开关系并播放对应讲解。

建议根据展厅优先级从 1、3、4 先落地（观感强、投资小），其余方向逐步迭代并复用同一套数据与 RAG 基础设施。
