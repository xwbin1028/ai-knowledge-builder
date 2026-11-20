"""
文件类型常量.

集中管理后缀白名单与默认输出目录, 节点里不写硬编码后缀.
"""
from typing import Final

# 单个后缀, 统一小写, 比较时对目标 .lower()
MD_SUFFIX: Final[str] = ".md"
PDF_SUFFIX: Final[str] = ".pdf"

# rglob 匹配模式
GLOB_MD_FILES: Final[str] = f"*{MD_SUFFIX}"

# 允许作为输入的扩展名白名单
ALLOWED_INPUT_SUFFIXES: Final[tuple[str, ...]] = (MD_SUFFIX, PDF_SUFFIX)

# 默认输出目录名, 拼到项目根目录下
DEFAULT_OUTPUT_DIR_NAME: Final[str] = "output"

# 支持的图片后缀白名单
SUPPORTED_IMAGE_SUFFIXES: Final[tuple[str, ...]] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
)
