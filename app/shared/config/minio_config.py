"""
MinIO 对象存储配置.

从 .env 读取连接信息 凭证 桶名与图片目录, 装配为全局单例 minio_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_bool, env_str


@dataclass
class MinIOConfig:
    """MinIO 对象存储配置项."""

    endpoint: str      # host:port
    access_key: str    # 访问 Key
    secret_key: str    # 访问 Secret
    bucket_name: str   # 默认桶名
    minio_img_dir: str  # 图片目录前缀
    minio_secure: bool  # 是否用 HTTPS


minio_config = MinIOConfig(
    endpoint=env_str("MINIO_ENDPOINT"),
    access_key=env_str("MINIO_ACCESS_KEY"),
    secret_key=env_str("MINIO_SECRET_KEY"),
    bucket_name=env_str("MINIO_BUCKET_NAME"),
    minio_img_dir=env_str("MINIO_IMG_DIR"),
    minio_secure=env_bool("MINIO_SECURE"),
)
