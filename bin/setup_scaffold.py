#!/usr/bin/env python3
"""Bootstrap the astronomy agent project structure and seed demo data.

The script is idempotent and safe to re-run. It creates directories, configuration
files, and small curated knowledge snippets so the interactive Q&A demo can run
immediately on a clean machine.
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

BASE = Path(__file__).resolve().parent.parent


def ensure_dirs() -> None:
    dirs = [
        BASE / "data/raw_pdf",
        BASE / "data/raw_img",
        BASE / "data/raw_docx",
        BASE / "data/raw_xls",
        BASE / "data/curated/faq",
        BASE / "data/curated/scripts",
        BASE / "data/curated/news",
        BASE / "data/curated/doc_ingest",
        BASE / "data/indexes",
        BASE / "outputs",
        BASE / "logs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def write_configs() -> None:
    (BASE / "configs/datasources.yaml").write_text(
        dedent(
            """
            # 数据源与采集计划（示例）
            datasources:
              - id: museum-internal
                type: pdf
                path: data/raw_pdf
                schedule: manual
              - id: museum-docx
                type: docx
                path: data/raw_docx
                schedule: manual
              - id: museum-photos
                type: image
                path: data/raw_img
                schedule: manual
              - id: museum-xls
                type: spreadsheet
                path: data/raw_xls
                schedule: manual
              - id: open-news
                type: rss
                path: https://www.nasa.gov/news-release/feed/
                schedule: daily
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (BASE / "configs/rag.yaml").write_text(
        dedent(
            """
            # RAG 路由与索引分区
            namespaces:
              - name: solar
                description: 太阳系展区讲解词、FAQ、新闻
                topk: 6
                rerank: true
              - name: deep_space
                description: 深空探索与航天器故事
                topk: 6
                rerank: true
              - name: kids
                description: 儿童友好简化版
                topk: 4
                rerank: false
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (BASE / "configs/personas.yaml").write_text(
        dedent(
            """
            personas:
              solar_guide:
                name: 太阳系展厅讲解员
                style: |
                  语气亲切，层次分明，会引用展柜位置与可观察现象，鼓励互动提问。
              deep_space_guide:
                name: 深空任务解说员
                style: |
                  强调探测器故事、任务时间线，适度加入航天趣闻。
              kids_guide:
                name: 儿童科普伙伴
                style: |
                  用比喻和提问引导，小句子，避免生僻词，鼓励孩子亲自动手或观察。
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (BASE / "configs/models.yaml").write_text(
        dedent(
            """
            # 模型配置：本地与联网默认值，脚本会自动写入，无需手动填充。
            local:
              provider: qwen2-1.5b-chat-int4
              # 放置量化后的 GGUF 权重路径；未下载时，auto_train.py 会创建占位符
              path: models/qwen2-1_5b-chat-int4.bin
              download_url: https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_0.gguf
              format: gguf

            online:
              provider: aliyun-qwen-max
              endpoint: https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
              model: qwen-max
              api_key_env: DASHSCOPE_API_KEY

            # 可切换的主流候选（不需修改代码，只需下载或配置 API Key 即可）
            presets:
              - name: qwen2.5-7b-instruct-gguf
                path: models/qwen2.5-7b-instruct-q4_0.gguf
                download_url: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_0.gguf
                format: gguf
              - name: llama-3.1-8b-instruct-gguf
                path: models/llama-3.1-8b-instruct-q4_0.gguf
                download_url: https://huggingface.co/unsloth/llama-3.1-8b-instruct-bnb-4bit-GGUF/resolve/main/model.q4_0.gguf
                format: gguf
              - name: glm-4-9b-chat-online
                endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
                model: glm-4-flash
                api_key_env: ZHIPU_API_KEY
              - name: moonshot-kimi-online
                endpoint: https://api.moonshot.cn/v1/chat/completions
                model: moonshot-v1-8k
                api_key_env: MOONSHOT_API_KEY
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def seed_faq() -> None:
    sample_faq = [
        {
            "id": "faq-solar-0001",
            "title": "太阳为什么会有黑子？",
            "persona": "solar_guide",
            "namespace": "solar",
            "audience": "teen",
            "tags": ["太阳", "黑子", "磁场"],
            "content": "太阳黑子是太阳表面磁场非常强的区域，磁场抑制了局部的热对流，所以温度比周围低，看起来更暗。",
            "source": "北京天文馆科普讲稿",
        },
        {
            "id": "faq-solar-0002",
            "title": "木星为什么有大红斑？",
            "persona": "solar_guide",
            "namespace": "solar",
            "audience": "adult",
            "tags": ["木星", "气旋", "风暴"],
            "content": "大红斑是一场持续数百年的巨大反气旋风暴，其能量来自木星内部和太阳辐射，风速可达每小时数百公里。",
            "source": "展品解说词",
        },
        {
            "id": "faq-deep-0001",
            "title": "旅行者一号现在在哪里？",
            "persona": "deep_space_guide",
            "namespace": "deep_space",
            "audience": "adult",
            "tags": ["旅行者一号", "星际空间"],
            "content": "旅行者一号已进入星际介质，距离太阳约240多亿公里，仍在用极低功率向地球发送数据。",
            "source": "NASA 公告 2024",
        },
        {
            "id": "faq-kids-0001",
            "title": "小朋友怎么理解月相变化？",
            "persona": "kids_guide",
            "namespace": "kids",
            "audience": "kid",
            "tags": ["月亮", "月相"],
            "content": "想象你拿着一个球做月亮，手电筒做太阳，转动球时亮的部分朝向你就像看到的月亮形状会变，这就是月相。",
            "source": "儿童活动教案",
        },
    ]
    (BASE / "data/curated/faq/faq.jsonl").write_text(
        "\n".join(json.dumps(rec, ensure_ascii=False) for rec in sample_faq) + "\n",
        encoding="utf-8",
    )


def seed_scripts() -> None:
    scripts = [
        {
            "id": "script-solar-entrance",
            "title": "太阳系展厅开场",
            "persona": "solar_guide",
            "namespace": "solar",
            "audience": "all",
            "content": dedent(
                """
                欢迎来到太阳系展厅！从这里开始，依次可以看到太阳、类地行星到气体巨行星的模型。
                请留意脚下的轨道刻度，每一步代表的时间和距离都不同。稍后可以在触摸屏上点击任意行星，听我讲它的故事。
                """
            ).strip(),
            "source": "展厅导览词",
        },
        {
            "id": "script-deepspace-jameswebb",
            "title": "詹姆斯·韦布空间望远镜亮点",
            "persona": "deep_space_guide",
            "namespace": "deep_space",
            "audience": "adult",
            "content": dedent(
                """
                这张深空照片来自詹姆斯·韦布空间望远镜。它在 L2 点运行，镜面直径 6.5 米，
                主要观测红外光，可以穿透尘埃云看到恒星正在诞生的地方。请注意图中那些红移明显的星系，它们记录了宇宙早期的历史。
                """
            ).strip(),
            "source": "展品图示讲解词",
        },
    ]
    (BASE / "data/curated/scripts/scripts.jsonl").write_text(
        "\n".join(json.dumps(rec, ensure_ascii=False) for rec in scripts) + "\n",
        encoding="utf-8",
    )


def seed_news() -> None:
    news_items = [
        {
            "id": "news-astro-20240801",
            "title": "中国新一代太阳观测卫星计划发布",
            "persona": "solar_guide",
            "namespace": "solar",
            "audience": "adult",
            "content": "最新计划显示，新卫星将携带多波段成像仪监测日冕物质抛射，对空间天气预警意义重大。",
            "source": "新华社科普频道",
        },
        {
            "id": "news-deep-20240715",
            "title": "欧洲木星冰卫星探测器完成中途轨道修正",
            "persona": "deep_space_guide",
            "namespace": "deep_space",
            "audience": "teen",
            "content": "探测器经过精确点火，修正后将按计划飞抵木星系统，未来将多次近距离飞掠木卫二以探测地下海洋。",
            "source": "ESA 新闻稿",
        },
    ]
    (BASE / "data/curated/news/news.jsonl").write_text(
        "\n".join(json.dumps(rec, ensure_ascii=False) for rec in news_items) + "\n",
        encoding="utf-8",
    )


def seed_raw_placeholders() -> None:
    (BASE / "data/raw_pdf/README.txt").write_text(
        "将原始 PDF 放在此目录，例如展品说明书、课程讲义。当前示例数据由 setup_scaffold 自动生成。\n",
        encoding="utf-8",
    )
    (BASE / "data/raw_img/README.txt").write_text(
        "将展品或观测图片放在此目录，后续可接 OCR/图像抽取脚本。\n",
        encoding="utf-8",
    )
    (BASE / "data/raw_docx/README.txt").write_text(
        "放置 Word/Docx 格式的展览大纲、讲解词。脚本会自动生成示例 docx。\n",
        encoding="utf-8",
    )
    (BASE / "data/raw_xls/README.txt").write_text(
        "放置 xls/xlsx 展品清单。脚本会自动生成示例工作簿。\n",
        encoding="utf-8",
    )


def seed_sample_docx() -> None:
    """Create a minimal docx (zip + XML) so newcomers can test docx ingestion."""

    docx_path = BASE / "data/raw_docx/exhibition_outline.docx"
    if docx_path.exists():
        return

    content_types = dedent(
        """
        <?xml version="1.0"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
        </Types>
        """
    ).strip()

    rels_xml = dedent(
        """
        <?xml version="1.0"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
        </Relationships>
        """
    ).strip()

    document_xml = dedent(
        """
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p><w:r><w:t>北京天文馆展览大纲（示例）</w:t></w:r></w:p>
            <w:p><w:r><w:t>展区：太阳系 —— 包含太阳、类地行星、气体巨行星模型。</w:t></w:r></w:p>
            <w:p><w:r><w:t>讲解词：围绕大红斑、日冕物质抛射、行星轨道比例等重点展开。</w:t></w:r></w:p>
            <w:p><w:r><w:t>互动：触摸屏问题引导 + 观测小任务。</w:t></w:r></w:p>
          </w:body>
        </w:document>
        """
    ).strip()

    with ZipFile(docx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", document_xml)


def seed_sample_xlsx() -> None:
    """Create a minimal xlsx spreadsheet describing exhibits to test parsing."""

    xlsx_path = BASE / "data/raw_xls/exhibit_inventory.xlsx"
    if xlsx_path.exists():
        return

    content_types = dedent(
        """
        <?xml version="1.0"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>
        """
    ).strip()

    rels_xml = dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
        </Relationships>
        """
    ).strip()

    workbook_xml = dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <sheets>
            <sheet name="exhibits" sheetId="1" r:id="rId1"/>
          </sheets>
        </workbook>
        """
    ).strip()

    workbook_rels = dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
        </Relationships>
        """
    ).strip()

    sheet1_xml = dedent(
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <sheetData>
            <row r="1">
              <c r="A1" t="inlineStr"><is><t>展品名</t></is></c>
              <c r="B1" t="inlineStr"><is><t>展区</t></is></c>
              <c r="C1" t="inlineStr"><is><t>亮点</t></is></c>
            </row>
            <row r="2">
              <c r="A2" t="inlineStr"><is><t>木星模型</t></is></c>
              <c r="B2" t="inlineStr"><is><t>太阳系</t></is></c>
              <c r="C2" t="inlineStr"><is><t>大红斑动态演示</t></is></c>
            </row>
            <row r="3">
              <c r="A3" t="inlineStr"><is><t>詹姆斯·韦布望远镜模型</t></is></c>
              <c r="B3" t="inlineStr"><is><t>深空</t></is></c>
              <c r="C3" t="inlineStr"><is><t>红外观测能力</t></is></c>
            </row>
          </sheetData>
        </worksheet>
        """
    ).strip()

    with ZipFile(xlsx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet1_xml)


def main() -> None:
    ensure_dirs()
    write_configs()
    seed_faq()
    seed_scripts()
    seed_news()
    seed_raw_placeholders()
    seed_sample_docx()
    seed_sample_xlsx()
    print("Project scaffold created. Demo data seeded in data/curated and placeholders in data/raw_*.")


if __name__ == "__main__":
    main()
