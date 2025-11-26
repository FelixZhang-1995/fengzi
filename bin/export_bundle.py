"""
将当前仓库打包为可直接下载的一键压缩包，便于在本地环境或离线机器上还原。
脚本会：
1. 自动创建 dist 目录；
2. 遍历仓库文件并过滤 .git、缓存目录；
3. 生成 zip 压缩包，命名包含时间戳；
4. 在控制台提示输出文件位置。
"""
from __future__ import annotations

import time
from pathlib import Path
import zipfile

# 定义需要跳过的目录/文件名（以任意层级匹配）
SKIP_PARTS = {
    '.git', 'dist', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.idea', '.DS_Store', '.venv', 'venv', '.ipynb_checkpoints'
}


def should_skip(path: Path) -> bool:
    """判断某个路径是否需要跳过。
    - 如果路径的任意部分在 SKIP_PARTS 中，则返回 True。
    """
    return any(part in SKIP_PARTS for part in path.parts)


def build_bundle() -> Path:
    """执行打包流程并返回生成的 zip 路径。"""
    # 仓库根目录：当前脚本所在目录的上一级（bin/ -> 项目根）
    repo_root = Path(__file__).resolve().parent.parent

    # dist 目录：用于存放打包产物
    dist_dir = repo_root / 'dist'
    dist_dir.mkdir(exist_ok=True)

    # 输出 zip 文件名，带时间戳防止覆盖
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    bundle_path = dist_dir / f'astro_agent_bundle_{timestamp}.zip'

    # 使用 ZIP_DEFLATED 进行压缩
    with zipfile.ZipFile(bundle_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in repo_root.rglob('*'):
            # 跳过目录或指定的忽略项
            if should_skip(path):
                continue
            if path.is_dir():
                continue

            # 计算相对路径以保持目录结构
            rel_path = path.relative_to(repo_root)
            zf.write(path, rel_path)

    return bundle_path


def main() -> None:
    """主入口：调用打包函数并打印结果。"""
    bundle_path = build_bundle()
    print('✅ 打包完成！')
    print(f'输出文件：{bundle_path}')
    print('现在可以把该 zip 复制/下载到本地，解压即可获得完整工程与脚本。')


if __name__ == '__main__':
    main()
