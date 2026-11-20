"""
LLM 与视觉模型配置.

从 .env 读取 OpenAI 兼容接口的地址 密钥 模型名与温度, 装配为全局单例 lm_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_float, env_str


@dataclass
class LLMConfig:
    """大语言模型与视觉模型配置项."""

    base_url: str        # API 基础地址, 例 https://host/v1
    api_key: str         # 鉴权密钥
    vl_model: str        # 视觉模型名, 对应 VL_MODEL
    llm_model: str       # 文本模型名, 对应 LLM_DEFAULT_MODEL
    llm_temperature: float  # 采样温度, 0-1


lm_config = LLMConfig(
    base_url=env_str("OPENAI_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
    vl_model=env_str("VL_MODEL"),
    llm_model=env_str("LLM_DEFAULT_MODEL"),
    llm_temperature=env_float("LLM_DEFAULT_TEMPERATURE"),
)
