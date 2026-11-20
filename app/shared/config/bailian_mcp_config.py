"""
DashScope MCP 联网检索配置.

从 .env 读取 MCP 服务地址与鉴权密钥, 装配为全局单例 mcp_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_str


@dataclass
class McpConfig:
    """MCP 服务配置项."""

    mcp_base_url: str  # MCP 服务地址
    api_key: str       # 鉴权密钥, 当前复用 OPENAI_API_KEY


mcp_config = McpConfig(
    mcp_base_url=env_str("MCP_DASHSCOPE_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
)
