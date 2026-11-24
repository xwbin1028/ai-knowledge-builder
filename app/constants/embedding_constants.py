"""
切片向量化常量.

职责: 定义 BGE-M3 向量维度 批大小 拼接分隔符与切片向量字段名.
"""
from typing import Final

# BGE-M3 输出稠密向量维度, 与 item_name 集合保持一致
BGE_M3_VECTOR_DIM: Final[int] = 1024

# 单批送给 BGE-M3 的切片数; 太大占内存, 太小降低吞吐
EMBEDDING_BATCH_SIZE: Final[int] = 5

# item_name 与 content 拼接时的分隔符
EMBEDDING_TEXT_SEPARATOR: Final[str] = ":"

# 切片上的向量字段名
CHUNK_FIELD_DENSE_VECTOR: Final[str] = "dense_vector"
CHUNK_FIELD_SPARSE_VECTOR: Final[str] = "sparse_vector"
