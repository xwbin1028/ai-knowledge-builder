"""
Milvus 向量库配置.

从 .env 读取连接地址与两个集合名, 装配为全局单例 milvus_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class MilvusConfig:
    """Milvus 连接与集合配置项."""

    milvus_url: str              # 连接地址, 例 http://localhost:19530
    chunks_collection: str       # 文本切片集合
    item_name_collection: str    # 主体名称集合


milvus_config = MilvusConfig(
    milvus_url=env_str("MILVUS_URL"),
    chunks_collection=env_str("CHUNKS_COLLECTION"),
    item_name_collection=env_str("ITEM_NAME_COLLECTION"),
)
