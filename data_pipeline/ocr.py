"""Minimal OCR/文本抽取示例.

If PaddleOCR is installed, it will be used. Otherwise the script falls back to
extracting text from TXT or simple PDF files using PyPDF2. This keeps the
pipeline runnable on a clean machine while still showing the full flow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def try_import_paddleocr():
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception:
        return None
    return PaddleOCR(use_angle_cls=True, lang="ch")


def extract_pdf_text(pdf_path: Path) -> List[str]:
    try:
        import PyPDF2  # type: ignore
    except Exception:
        return []
    texts = []
    reader = PyPDF2.PdfReader(str(pdf_path))
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return texts


def process(file_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ocr = try_import_paddleocr()
    records = []
    if ocr:
        pages = ocr.ocr(str(file_path), cls=True)
        for i, page in enumerate(pages):
            for line, (bbox, (text, prob)) in enumerate(page):
                records.append({
                    "page": i,
                    "line": line,
                    "text": text,
                    "prob": prob,
                    "bbox": bbox,
                    "source_file": file_path.name,
                })
    elif file_path.suffix.lower() == ".pdf":
        texts = extract_pdf_text(file_path)
        for i, text in enumerate(texts):
            records.append({"page": i, "text": text, "prob": 1.0, "bbox": [], "source_file": file_path.name})
    else:
        content = file_path.read_text(encoding="utf-8")
        records.append({"page": 0, "text": content, "prob": 1.0, "bbox": [], "source_file": file_path.name})
    out_path = out_dir / f"{file_path.stem}.json"
    out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Run OCR/text extraction on a file")
    parser.add_argument("input", type=Path, help="Path to PDF/TXT/image file")
    parser.add_argument("output", type=Path, help="Output directory to save JSON")
    args = parser.parse_args()

    out_path = process(args.input, args.output)
    print(f"Saved OCR/文本抽取结果: {out_path}")


if __name__ == "__main__":
    main()
