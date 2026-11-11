"""
MinIO 对象存储配置模块。
负责从环境变量中读取对象存储服务 MinIO 的连接地址 凭证与存储路径等配置，
并将其封装为强类型的全局单例实例 minio_config 供业务代码直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_bool, env_str


# ---------------------------------------------------------------------------
# 配置模型定义
# ---------------------------------------------------------------------------
@dataclass
class MinIOConfig:
    """
    MinIO 对象存储配置项的数据类。

    Attributes:
        endpoint (str): MinIO 服务的连接地址。
        access_key (str): 访问鉴权所用的 Access Key。
        secret_key (str): 访问鉴权所用的 Secret Key。
        bucket_name (str): 默认使用的存储桶名称。
        minio_img_dir (str): 存储图片的默认目录前缀。
        minio_secure (bool): 是否启用安全传输协议 HTTPS。
    """
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str
    minio_img_dir: str
    minio_secure: bool


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
minio_config = MinIOConfig(
    endpoint=env_str("MINIO_ENDPOINT"),
    access_key=env_str("MINIO_ACCESS_KEY"),
    secret_key=env_str("MINIO_SECRET_KEY"),
    bucket_name=env_str("MINIO_BUCKET_NAME"),
    minio_img_dir=env_str("MINIO_IMG_DIR"),
    minio_secure=env_bool("MINIO_SECURE"),
)
