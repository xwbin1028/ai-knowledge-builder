"""
文档切分常量.

职责: 定义切分阈值 标题规则 分隔符与备份文件名, 切分服务只读这里.
"""
from typing import Final

# 单个切片的上限, 合并后超过它会降低检索精度
CHUNK_MAX_SIZE: Final[int] = 1000

# 单个切片的基准长度, 超过它交给递归切割器细切
CHUNK_SIZE: Final[int] = 600

# 相邻切片的字符重叠, 保证切断处的语义仍然连贯
CHUNK_OVERLAP: Final[int] = 50

# 短碎片阈值, 低于它尝试与同标题的下一片合并
CHUNK_MIN: Final[int] = 400

# 标题行: 行首最多 3 个空格, 1-6 个 #, 后接空格与标题文字
TITLE_PATTERN: Final[str] = r"^ {0,3}#{1,6}\s+\S"

# 文档开头没有标题时, 这段内容的兜底标题
PREAMBLE_TITLE: Final[str] = "前言"

# 切分备份文件名后缀, 与 Markdown 放在同一目录
CHUNKS_JSON_SUFFIX: Final[str] = "_chunks.json"

# 旧版备份文件名, 读取时兼容
LEGACY_CHUNKS_JSON_NAME: Final[str] = "chunks.json"

# 递归切割器的分隔符, 从段落 行 逐级退化到中文句读
SPLIT_SEPARATORS: Final[tuple[str, ...]] = ("\n\n", "\n", "。", "！", "？", "；")

# 代码块围栏, 围栏内的 # 不当作标题
CODE_FENCE_MARKERS: Final[tuple[str, ...]] = ("```", "~~~")
