#!/usr/bin/env python3
"""
把 Word/Docx 展览大纲和 xls/xlsx 展品清单转换成 JSONL 结构化文本，
用于 RAG 或微调前的数据准备。

每一行都加入中文注释，方便零基础用户理解。
"""

from __future__ import annotations

import json  # 处理 JSON 序列化
import xml.etree.ElementTree as ET  # 解析 docx/xlsx 内部的 XML 结构
from pathlib import Path  # 文件路径拼装与遍历
from typing import List, Dict  # 类型注解，帮助读者理解返回值
from zipfile import ZipFile  # docx/xlsx 本质是 zip 包，需要用 ZipFile 解压读取

# 项目根目录，方便在任意位置运行脚本
BASE = Path(__file__).resolve().parent.parent

# 原始 docx、xls/xlsx 存放目录
DOCX_DIR = BASE / "data/raw_docx"
XLS_DIR = BASE / "data/raw_xls"

# 解析后写入的 JSONL 目标目录
OUTPUT_DIR = BASE / "data/curated/doc_ingest"
OUTPUT_FILE = OUTPUT_DIR / "doc_ingest.jsonl"


def extract_docx_text(docx_path: Path) -> str:
    """从 docx 中提取段落纯文本。"""

    # 使用 ZipFile 打开 docx 压缩包
    with ZipFile(docx_path) as zf:
        # 读取主文档 XML
        with zf.open("word/document.xml") as f:
            xml_bytes = f.read()

    # 解析 XML 为树结构
    root = ET.fromstring(xml_bytes)

    # 定义命名空间前缀，docx 的 XML 标签使用 w 前缀
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    # 找到所有文本节点 <w:t>，逐个提取文字
    texts: List[str] = []
    for node in root.findall(".//w:t", ns):
        texts.append((node.text or "").strip())

    # 过滤空行，并用换行拼接
    filtered = [t for t in texts if t]
    return "\n".join(filtered)


def extract_xlsx_rows(xlsx_path: Path) -> List[List[str]]:
    """从 xlsx 读取 sheet1 的所有行（仅解析 inlineStr 文本单元格）。"""

    # 打开 xlsx 压缩包
    with ZipFile(xlsx_path) as zf:
        # 读取工作表 XML
        with zf.open("xl/worksheets/sheet1.xml") as f:
            xml_bytes = f.read()

    # 解析 XML
    root = ET.fromstring(xml_bytes)

    # 存放行数据的列表
    rows: List[List[str]] = []

    # 遍历每一行 <row>
    for row in root.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/"
                             "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        # 当前行的单元格值列表
        current_row: List[str] = []

        # 遍历单元格 <c>，本示例使用 inlineStr 存放文本
        for cell in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            # 找到内嵌字符串 <is>/<t>
            is_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is")
            if is_node is None:
                current_row.append("")
                continue
            text_node = is_node.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
            current_row.append((text_node.text or "").strip())

        # 将该行加入 rows
        rows.append(current_row)

    return rows


def convert_rows_to_records(rows: List[List[str]]) -> List[Dict[str, str]]:
    """将二维表格行转换为结构化字典列表，方便 JSONL 写入。"""

    # 如果没有数据，直接返回空列表
    if not rows:
        return []

    # 第一行作为表头
    header = rows[0]

    # 余下的行为数据
    records: List[Dict[str, str]] = []
    for row in rows[1:]:
        # 对齐长度，防止列数不一致
        padded = row + [""] * (len(header) - len(row))
        record = {header[i]: padded[i] for i in range(len(header))}
        records.append(record)

    return records


def ensure_output_dir() -> None:
    """确保输出目录存在。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_ingestion() -> None:
    """执行 docx 和 xls/xlsx 的解析并写入 JSONL。"""

    ensure_output_dir()

    # 存放所有记录的列表
    all_records: List[Dict[str, str]] = []

    # 遍历 docx 目录
    for docx_file in DOCX_DIR.glob("*.docx"):
        text = extract_docx_text(docx_file)
        all_records.append(
            {
                "type": "docx",
                "file": docx_file.name,
                "content": text,
                "namespace": "solar",
                "persona": "solar_guide",
                "source": "docx_ingest",
            }
        )

    # 遍历 xls/xlsx 目录
    for xls_file in list(XLS_DIR.glob("*.xlsx")) + list(XLS_DIR.glob("*.xls")):
        rows = extract_xlsx_rows(xls_file)
        records = convert_rows_to_records(rows)
        all_records.append(
            {
                "type": "spreadsheet",
                "file": xls_file.name,
                "records": records,
                "namespace": "solar",
                "persona": "solar_guide",
                "source": "xls_ingest",
            }
        )

    # 将所有记录写入 JSONL
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Ingested {len(all_records)} files -> {OUTPUT_FILE}")


if __name__ == "__main__":
    run_ingestion()
