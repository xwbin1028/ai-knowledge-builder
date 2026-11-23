"""
Milvus 网关.

职责: 统一提供集合名与客户端, 业务侧不直接读配置.
边界: 不负责建集合与读写数据.
"""
from pymilvus import MilvusClient

from app.infra.config.providers import infra_config
from app.shared.clients.milvus_utils import get_milvus_client


class MilvusGateway:
    """Milvus 配置与访问入口, 全局单例 milvus_gateway."""

    @property
    def chunks_collection(self) -> str:
        """文档切片集合名."""
        return infra_config.milvus.chunks_collection

    @property
    def item_name_collection(self) -> str:
        """主体名称集合名."""
        return infra_config.milvus.item_name_collection

    @property
    def client(self) -> MilvusClient:
        """全局 Milvus 客户端."""
        return get_milvus_client()


# 全局唯一网关, 全项目复用
milvus_gateway = MilvusGateway()
