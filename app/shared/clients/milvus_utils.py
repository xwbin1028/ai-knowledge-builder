"""
Milvus 客户端工具.

职责: 懒加载并复用全局 MilvusClient.
边界: 不建集合, 不读写数据.
"""
from pymilvus import MilvusClient

from app.shared.config.milvus_config import milvus_config
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import logger

# 全局客户端, 首次调用时创建
_milvus_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """
    获取全局 Milvus 客户端.

    业务逻辑:
        1. 已初始化则直接返回
        2. 校验 MILVUS_URL
        3. 创建客户端并缓存

    Returns:
        MilvusClient: 全局复用客户端.

    Raises:
        ValueError: 缺少 MILVUS_URL.
        RuntimeError: 客户端初始化失败.
    """
    global _milvus_client

    # 1. 已初始化则直接返回
    if _milvus_client is not None:
        return _milvus_client

    # 2. 校验 MILVUS_URL
    if not milvus_config.milvus_url:
        raise business_error(ValueError, "", "Milvus 配置缺失", field="MILVUS_URL")

    # 3. 创建客户端并缓存
    try:
        _milvus_client = MilvusClient(uri=milvus_config.milvus_url)
    except Exception as exc:
        raise business_error(RuntimeError, "", "Milvus 客户端初始化失败", error=exc) from exc

    logger.info(f"[提示] Milvus 客户端就绪 | uri={milvus_config.milvus_url}")
    return _milvus_client
