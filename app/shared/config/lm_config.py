"""
LLM 配置模块。
负责从环境变量中读取大语言模型 (LLM)与视觉模型 (VL)相关的配置参数，
并将其封装为强类型的全局单例实例 lm_config，供业务代码开箱即用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_float, env_str


# ---------------------------------------------------------------------------
# 配置模型定义
# ---------------------------------------------------------------------------
@dataclass
class LLMConfig:
    """
    大语言模型相关配置项的数据类。

    Attributes:
        base_url (str): API 请求的基础 URL。
        api_key (str): 鉴权所需的 API Key。
        lv_model (str): 视觉语言模型 (Vision-Language) 的名称或标识。
        llm_model (str): 纯文本大语言模型的名称或标识。
        llm_temperature (float): 生成内容的随机性参数 (0.0 ~ 1.0)
    """
    base_url: str
    api_key: str
    lv_model: str
    llm_model: str
    llm_temperature: float


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
lm_config = LLMConfig(
    base_url=env_str("OPENAI_BASE_URL"),
    api_key=env_str("OPENAI_API_KEY"),
    lv_model=env_str("VL_MODEL"),
    llm_model=env_str("LLM_DEFAULT_MODEL"),
    llm_temperature=env_float("LLM_DEFAULT_TEMPERATURE")
)
