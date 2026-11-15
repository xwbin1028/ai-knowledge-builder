"""
文件相关常量定义。

集中管理文件类型白名单等业务常量，避免在多个节点中散落硬编码。
"""
from typing import Final


# 单个后缀常量（统一小写存储，比较时对目标后缀 .lower()）
MD_SUFFIX: Final[str] = ".md"
PDF_SUFFIX: Final[str] = ".pdf"

# 允许作为输入文件的扩展名白名单
ALLOWED_INPUT_SUFFIXES: Final[tuple[str, ...]] = (MD_SUFFIX, PDF_SUFFIX)
