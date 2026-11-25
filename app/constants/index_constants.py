"""
切片入库常量.

职责: 定义 chunks 集合的字段名 文本长度 与向量索引参数.
"""
from typing import Final

# chunks 集合的标量字段名
CHUNK_FIELD_CHUNK_ID: Final[str] = "chunk_id"
CHUNK_FIELD_FILE_TITLE: Final[str] = "file_title"
CHUNK_FIELD_ITEM_NAME: Final[str] = "item_name"
CHUNK_FIELD_PARENT_TITLE: Final[str] = "parent_title"
CHUNK_FIELD_TITLE: Final[str] = "title"
CHUNK_FIELD_PART: Final[str] = "part"
CHUNK_FIELD_CONTENT: Final[str] = "content"

# VARCHAR 字段最大长度
CHUNK_TEXT_MAX_LENGTH: Final[int] = 600
CHUNK_CONTENT_MAX_LENGTH: Final[int] = 65535

# 稠密向量索引参数, 与 item_name 集合保持一致
CHUNK_DENSE_INDEX_NAME: Final[str] = "dense_vector_index"
CHUNK_DENSE_INDEX_TYPE: Final[str] = "HNSW"
CHUNK_DENSE_METRIC_TYPE: Final[str] = "COSINE"
CHUNK_HNSW_M: Final[int] = 64
CHUNK_HNSW_EF_CONSTRUCTION: Final[int] = 100

# 稀疏向量索引参数
CHUNK_SPARSE_INDEX_NAME: Final[str] = "sparse_vector_index"
CHUNK_SPARSE_INDEX_TYPE: Final[str] = "SPARSE_INVERTED_INDEX"
CHUNK_SPARSE_METRIC_TYPE: Final[str] = "IP"
CHUNK_SPARSE_INVERTED_ALGO: Final[str] = "SINDI"
