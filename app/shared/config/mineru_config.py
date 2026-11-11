"""
MinerU 文档解析服务配置模块。
负责从环境变量中读取文档解析服务(MinerU)的服务地址与鉴权 Token，
并将其封装为强类型的全局单例实例 mineru_config，供文档解析业务直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_str


@dataclass
class MinerUConfig:
    """
    MinerU 文档解析服务配置项的数据类。

    Attributes:
        base_url (str): MinerU 服务的 API 基础请求地址。
        api_key (str): 请求 MinerU 服务时所需的鉴权 Token。
    """
    base_url: str
    api_key: str


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
mineru_config = MinerUConfig(
    base_url=env_str("MINERU_BASE_URL"),
    api_key=env_str("MINERU_API_TOKEN"),
)
