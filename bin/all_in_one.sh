#!/usr/bin/env bash

# =============================================
# 一键生成目录、示例数据、假训练产物与可运行的交互式问答应用
# 适合零基础用户：直接执行本脚本即可完成初始化与简单自测
# =============================================

# 遇到错误立即退出，避免产生不完整的文件
set -euo pipefail

# 取得仓库根目录，确保在任意位置运行都能定位到工程
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[信息] 当前工程目录：$ROOT_DIR"

# 检查 Python 是否可用（Mac 自带，也可使用 pyenv/conda）
if ! command -v python >/dev/null 2>&1; then
  echo "[错误] 未检测到 python 命令，请先安装 Python 3.9+ 后再重试。"
  exit 1
fi

# 1/4：创建目录结构、写入配置与示例数据（含 docx/xls 占位文件）
echo "[步骤 1/4] 运行脚手架，生成文件与示例数据..."
python "$ROOT_DIR/bin/setup_scaffold.py"

# 2/4：模拟训练，生成占位模型与指标文件，方便后续流程联调
echo "[步骤 2/4] 执行自动化假训练，生成占位权重..."
python "$ROOT_DIR/bin/auto_train.py"

# 3/4：将 Word 展览大纲、Excel 展品清单解析为 RAG 可用的 JSONL
echo "[步骤 3/4] 解析 office 样例文件，生成结构化数据..."
python "$ROOT_DIR/data_pipeline/ingest_office.py"

# 4/4：启动一次演示问答（使用默认 persona），验证流程畅通
echo "[步骤 4/4] 运行演示问答，确认应用可用..."
python "$ROOT_DIR/services/orchestrator.py" "请简单介绍太阳系的行星"

# 可选：打包成 zip，便于拷贝到离线设备
echo "[可选] 如需打包离线分发，可执行：python bin/export_bundle.py"

echo "[完成] 一键生成与验证已完成。如需再次运行，可直接执行本脚本。"
