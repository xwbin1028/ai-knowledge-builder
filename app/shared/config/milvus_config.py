"""
Milvus 配置模块。
负责从环境变量中读取向量数据库(Milvus)的连接地址与集合名称，
并将其封装为强类型的全局单例实例 milvus_config，供 RAG 与检索业务直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_str


@dataclass
class MilvusConfig:
    """
    Milvus 向量数据库配置项的数据类。

    Attributes:
        milvus_url (str): Milvus 服务的连接地址(如 http://localhost:19530)
        chunks_collection (str): 存放文档切块(Chunks) 向量数据的集合名称。
        entity_name_collection (str): 存放实体名称(Entity Name)向量数据的集合名称。
        item_name_collection (str): 存放物品名称(Item Name)向量数据的集合名称。
    """
    milvus_url: str
    chunks_collection: str
    entity_name_collection: str
    item_name_collection: str

milvus_config = MilvusConfig(
    milvus_url=env_str("MILVUS_URL"),
    chunks_collection=env_str("CHUNKS_COLLECTION"),
    entity_name_collection=env_str("ENTITY_NAME_COLLECTION"),
    item_name_collection=env_str("ITEM_NAME_COLLECTION"),
)
