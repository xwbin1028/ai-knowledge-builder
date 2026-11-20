"""
MinIO 客户端工具.

单进程懒加载, 未加锁; 首次调用时创建连接并确保桶存在, 后续复用同一客户端.
"""
import json

from minio import Minio

from app.shared.config.minio_config import minio_config
from app.shared.runtime.logger import logger

# 全局客户端, 首次调用时创建
_minio_client: Minio | None = None


# ---------------------------------------------------------------------------
# 客户端与桶
# ---------------------------------------------------------------------------
def _create_minio_client() -> Minio:
    """按全局配置创建 MinIO 客户端."""
    return Minio(
        endpoint=minio_config.endpoint,
        access_key=minio_config.access_key,
        secret_key=minio_config.secret_key,
        secure=minio_config.minio_secure,
    )


def _build_bucket_policy(bucket_name: str) -> str:
    """
    生成桶的公开读策略.

    Args:
        bucket_name: 桶名.

    Returns:
        str: S3 策略 JSON.
    """
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            }
        ],
    }
    return json.dumps(policy)


def _ensure_bucket(client: Minio) -> None:
    """
    确保桶存在并设置公开读策略.

    业务逻辑:
        1. 从配置取桶名
        2. 桶已存在则返回
        3. 不存在则创建并设置策略
    """
    # 1. 从配置取桶名
    bucket_name = minio_config.bucket_name

    # 2. 桶已存在则返回
    if client.bucket_exists(bucket_name):
        logger.info(f"[提示] MinIO 桶已存在 | bucket={bucket_name}")
        return

    # 3. 不存在则创建并设置策略
    client.make_bucket(bucket_name)
    client.set_bucket_policy(bucket_name, _build_bucket_policy(bucket_name))
    logger.info(f"[提示] MinIO 桶已创建 | bucket={bucket_name} | policy=public-read")


def get_minio_client() -> Minio:
    """
    获取全局 MinIO 客户端.

    业务逻辑:
        1. 已初始化则直接返回
        2. 创建客户端并确保桶就绪
        3. 缓存后返回

    Returns:
        Minio: 全局复用客户端.
    """
    global _minio_client

    # 1. 已初始化则直接返回
    if _minio_client is not None:
        return _minio_client

    # 2. 创建客户端并确保桶就绪
    logger.info("[提示] MinIO 客户端初始化")
    client = _create_minio_client()
    _ensure_bucket(client)

    # 3. 缓存后返回
    _minio_client = client
    return _minio_client
