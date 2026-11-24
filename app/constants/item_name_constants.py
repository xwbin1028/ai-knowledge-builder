"""
主体名称识别常量.

职责: 定义识别上下文条数 兜底标题 与 item_name 集合的结构参数.
"""
from typing import Final

from app.constants.embedding_constants import BGE_M3_VECTOR_DIM

# 送给模型的切片条数, 过多会稀释主体名称
ITEM_NAME_RECOGNITION_CHUNKS_TOP_K: Final[int] = 3

# file_title 缺失时的兜底标题
DEFAULT_FILE_TITLE: Final[str] = "default_title"

# item_name 集合的字段名
ITEM_NAME_FIELD_PK: Final[str] = "pk"
ITEM_NAME_FIELD_FILE_TITLE: Final[str] = "file_title"
ITEM_NAME_FIELD_ITEM_NAME: Final[str] = "item_name"
ITEM_NAME_FIELD_DENSE_VECTOR: Final[str] = "dense_vector"
ITEM_NAME_FIELD_SPARSE_VECTOR: Final[str] = "sparse_vector"

# VARCHAR 字段最大长度
ITEM_NAME_TEXT_MAX_LENGTH: Final[int] = 600

# BGE-M3 稠密向量维度, 与切片向量共用
ITEM_NAME_VECTOR_DIM: Final[int] = BGE_M3_VECTOR_DIM

# 稠密向量索引参数
ITEM_NAME_DENSE_INDEX_NAME: Final[str] = "dense_vector_index"
ITEM_NAME_DENSE_INDEX_TYPE: Final[str] = "HNSW"
ITEM_NAME_DENSE_METRIC_TYPE: Final[str] = "COSINE"
ITEM_NAME_HNSW_M: Final[int] = 64
ITEM_NAME_HNSW_EF_CONSTRUCTION: Final[int] = 100

# 稀疏向量索引参数
ITEM_NAME_SPARSE_INDEX_NAME: Final[str] = "sparse_vector_index"
ITEM_NAME_SPARSE_INDEX_TYPE: Final[str] = "SPARSE_INVERTED_INDEX"
ITEM_NAME_SPARSE_METRIC_TYPE: Final[str] = "IP"
ITEM_NAME_SPARSE_INVERTED_ALGO: Final[str] = "DAAT_MAXSCORE"
