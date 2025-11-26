# fengzi
本仓库用于沉淀北京天文馆科普大模型的技术资料与可运行示例。

## 快速开始（本仓库示例）
0. **懒人一键执行**：直接运行 Bash 脚本完成所有初始化、假训练、Office 解析与演示问答。
   ```bash
   bash bin/all_in_one.sh
   ```
   - 若想单独控制某一步，再按下方 1~4 的细分指令执行。
1. 运行初始化脚本，创建完整目录结构并写入示例数据（会同时写入本地/联网模型默认配置）：
   ```bash
   python bin/setup_scaffold.py
   ```
   - 默认本地模型：Qwen2-1.5B-Instruct（GGUF 量化占位路径 `models/qwen2-1_5b-chat-int4.bin`，脚本会自动生成占位文件）
   - 默认联网模型：通义千问 Qwen-Max（API Key 可通过环境变量 `DASHSCOPE_API_KEY` 提供）
2. 一键生成“已训练”占位模型与关键字缓存，避免手动填参：
   ```bash
   python bin/auto_train.py
   ```
3. 将 Word 大纲、讲解词和 xls/xlsx 展品清单转成 JSONL 供检索：
   ```bash
   python data_pipeline/ingest_office.py
   ```
   - 示例 docx/xlsx 已由 `setup_scaffold.py` 自动生成，运行后会在 `data/curated/doc_ingest/doc_ingest.jsonl` 看到解析结果。
3. 启动交互式问答讲解应用，模拟游客在展厅触摸屏前的对话：
   ```bash
   python services/interactive_app.py --persona solar_guide
   ```
   - 若面向儿童可切换：`--persona kids_guide`
   - 深空任务讲解：`--persona deep_space_guide`
4. 单条提问调试，可输出结构化 JSON：
   ```bash
   python services/orchestrator.py "给我介绍一下木星的大红斑"
   ```

更完整的技术蓝图、数据治理与训练路线详见 `docs/astro_agent_blueprint.md`。

## 单机（Mac Studio）从 0 开始部署工作流
1. **准备环境**：
   - 安装 Homebrew（若未安装）：`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
   - 安装 Python 3.11+：`brew install python@3.11`
   - 创建虚拟环境：`python3 -m venv .venv && source .venv/bin/activate`
   - 安装依赖：`pip install -r requirements.txt`（若无 requirements，可先运行脚本，按提示补齐 `python-docx`/`pandas` 等）
2. **初始化项目与示例数据**：`python bin/setup_scaffold.py`
   - 自动生成目录、示例 docx/xlsx/PDF 占位、默认模型配置。
3. **模拟训练占位模型**：`python bin/auto_train.py`
   - 生成 `outputs/trained_stub.json` 与占位模型权重，后续可替换为真实下载的 GGUF 或 ONNX 权重。
4. **解析 Office 文档**：`python data_pipeline/ingest_office.py`
   - 把 Word 讲解词、xls/xlsx 展品清单转成 JSONL，便于 RAG 索引。
5. **运行交互问答**：
   - 文本/CLI：`python services/interactive_app.py --persona solar_guide`
   - 单条调试：`python services/orchestrator.py "儿童能看到的木星亮点？"`
6. **切换主流模型**：
   - 本地轻量：Qwen2-1.5B、Qwen2.5-7B（GGUF/FP16 均可，本地下载后更新 `configs/models.yaml` 的 `path`）。
   - 本地中型：Llama 3.1-8B、GLM-4-9B（需更大显存，可用 M2 Ultra 共享内存或外接 GPU 盒）。
   - 联网高阶：Qwen-Max、Moonshot-Kimi、GPT-4o、Gemini 1.5 Pro（在 `configs/models.yaml` 写入 endpoint & 模型名，export API Key 环境变量）。
7. **后续增强**：
   - 替换占位模型为真实权重，接入 GPU/Metal 加速推理。
   - 对 `data/curated` 新增自有展品文本，重建向量索引（可扩展为 FAISS/Milvus）。
   - 在 `services/interactive_app.py` 内增添语音 TTS/ASR 入口，连到展厅触摸屏或机器人 SDK。

## 一键打包下载
若你只想把当前完整工程打成压缩包便于下载或拷贝到其他机器，执行：

```bash
python bin/export_bundle.py
```

- 脚本会在 `dist/` 生成形如 `astro_agent_bundle_YYYYMMDD_HHMMSS.zip` 的文件。
- 已自动忽略 `.git`、缓存目录和虚拟环境，解压即可得到与当前仓库一致的目录结构与脚本。

### 无法传输二进制文件时的纯文本方案
部分内网或管理平台会拦截 zip 等二进制文件，此时可改用纯文本自解压脚本：

```bash
python bin/make_self_extract.py
```

- 会在 `dist/` 生成 `astro_agent_self_extract.sh`，文件内容为纯文本（内嵌 base64）。
- 将该 `.sh` 单文件复制到目标机器后运行：
  ```bash
  bash astro_agent_self_extract.sh [目标目录，可选，默认 self_extract_output]
  ```
- 脚本会自动解码并还原完整的工程目录，适用于“拉取时显示不支持二进制文件”的场景。
