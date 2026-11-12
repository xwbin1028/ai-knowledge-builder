"""
MCP 联网检索配置模块。

负责从环境变量中读取 MCP 服务的请求地址与鉴权密钥，
并将其封装为全局单例实例 mcp_config 供联网检索业务直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_str


# ---------------------------------------------------------------------------
# 配置模型定义
# ---------------------------------------------------------------------------
@dataclass
class McpConfig:
    """
    MCP 服务配置项的数据类。

    Attributes:
        mcp_base_url (str): MCP 服务的基础请求地址。
        api_key (str): 请求服务所需的鉴权密钥。
    """
    mcp_base_url: str
    api_key: str


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
mcp_config = McpConfig(
    mcp_base_url=env_str("MCP_DASHSCOPE_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
)
