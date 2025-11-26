"""
生成纯文本自解压安装脚本，便于在不支持二进制传输的环境下获取完整项目。
实现思路：
1) 复用与 export_bundle 一样的打包过滤逻辑，将仓库打成 zip；
2) 将 zip 转为 base64 文本嵌入 shell 脚本；
3) 生成 dist/astro_agent_self_extract.sh，自带中文说明，执行后自动还原项目目录。
"""
from __future__ import annotations

import base64
import time
from pathlib import Path
import zipfile

SKIP_PARTS = {
    '.git', 'dist', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.idea', '.DS_Store', '.venv', 'venv', '.ipynb_checkpoints'
}


def should_skip(path: Path) -> bool:
    """判断路径是否需要跳过。"""
    return any(part in SKIP_PARTS for part in path.parts)


def build_zip(repo_root: Path, dist_dir: Path) -> Path:
    """将仓库内容（过滤缓存/隐藏目录）打包为 zip。"""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    zip_path = dist_dir / f'astro_agent_bundle_{timestamp}.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in repo_root.rglob('*'):
            if should_skip(path) or path.is_dir():
                continue
            zf.write(path, path.relative_to(repo_root))
    return zip_path


def write_self_extract(dist_dir: Path, zip_path: Path) -> Path:
    """生成自解压 shell 文件，将 zip 的 base64 文本嵌入其中。"""
    # 读取压缩包并编码
    payload = base64.b64encode(zip_path.read_bytes()).decode('ascii')
    out_path = dist_dir / 'astro_agent_self_extract.sh'

    script = f"""#!/usr/bin/env bash
# 这是一个纯文本自解压脚本，适用于无法直接传输二进制压缩包的环境。
# 用法：
#   1) bash astro_agent_self_extract.sh [目标目录]
#   2) 默认会在当前目录下创建 self_extract_output/ 并解压工程。
# 说明：脚本内嵌了 base64 编码的 zip 包，运行时会自动解码并解压。
set -euo pipefail

TARGET_DIR=${{1:-self_extract_output}}
mkdir -p "$TARGET_DIR"
TMP_ZIP="$TARGET_DIR/_bundle.zip"

cat > "$TARGET_DIR/_bundle.b64" <<'EOF_PAYLOAD'
{payload}
EOF_PAYLOAD

base64 --decode "$TARGET_DIR/_bundle.b64" > "$TMP_ZIP"
unzip -oq "$TMP_ZIP" -d "$TARGET_DIR"
rm "$TARGET_DIR/_bundle.b64" "$TMP_ZIP"

echo "✅ 已还原项目文件到: $TARGET_DIR"
"""

    out_path.write_text(script, encoding='utf-8')
    out_path.chmod(0o755)
    return out_path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root / 'dist'
    dist_dir.mkdir(exist_ok=True)

    zip_path = build_zip(repo_root, dist_dir)
    sh_path = write_self_extract(dist_dir, zip_path)

    print('✅ 自解压脚本已生成！')
    print(f'- 自解压脚本: {sh_path}')
    print(f'- 原始压缩包: {zip_path}')
    print('提示：如果目标机器限制二进制传输，只需复制 astro_agent_self_extract.sh 到目标机运行即可。')


if __name__ == '__main__':
    main()
