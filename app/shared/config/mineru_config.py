"""
MinerU 解析服务配置.

从 .env 读取服务地址与鉴权 Token, 装配为全局单例 mineru_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class MinerUConfig:
    """MinerU 服务配置项."""

    base_url: str  # 服务地址
    api_key: str   # 鉴权 Token, 对应 MINERU_API_TOKEN


mineru_config = MinerUConfig(
    base_url=env_str("MINERU_BASE_URL"),
    api_key=env_str("MINERU_API_TOKEN"),
)
