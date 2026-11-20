"""
LLM 客户端工厂.

按 模型名 + JSON 模式缓存 ChatOpenAI 实例, 配置统一来自 lm_config.
"""
from langchain_core.exceptions import LangChainException
from langchain_openai import ChatOpenAI

from app.shared.config.lm_config import lm_config
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import logger

_DEFAULT_LLM_MODEL = "qwen3.8-flash"
_DEFAULT_TEMPERATURE = 0.1

# 缓存键: 模型名 + JSON 模式
_llm_client_cache: dict[tuple[str, bool], ChatOpenAI] = {}


def get_llm_client(model: str | None = None, json_mode: bool = False) -> ChatOpenAI:
    """
    获取或创建 ChatOpenAI 客户端.

    适配 OpenAI 兼容接口, 如千问 即梦. 命中缓存直接复用.

    业务逻辑:
        1. 确定模型名与缓存键
        2. 命中缓存则返回
        3. 校验 api_key 与 base_url
        4. 组装 extra_body 与 model_kwargs
        5. 创建客户端并写入缓存

    Args:
        model: 模型名, 优先级 入参 > lm_config.llm_model > 默认值.
        json_mode: 是否开启 JSON 输出模式.

    Returns:
        ChatOpenAI: 可复用的客户端实例.

    Raises:
        ValueError: 缺失 API 密钥或地址.
        RuntimeError: LangChain 层初始化失败.
    """
    # 1. 确定模型名与缓存键
    target_model = model or lm_config.llm_model or _DEFAULT_LLM_MODEL
    cache_key = (target_model, json_mode)

    # 2. 命中缓存则返回
    if cache_key in _llm_client_cache:
        logger.debug(f"[调试] LLM 客户端缓存命中 | model={target_model} | json_mode={json_mode}")
        return _llm_client_cache[cache_key]

    # 3. 校验 api_key 与 base_url
    if not lm_config.api_key:
        raise business_error(ValueError, "", "LLM 配置缺失", field="OPENAI_API_KEY")
    if not lm_config.base_url:
        raise business_error(ValueError, "", "LLM 配置缺失", field="OPENAI_BASE_URL")

    # 4. 组装 extra_body 与 model_kwargs
    # 千问系列私有参数: 关闭思考链, 减少冗余输出
    extra_body = {"enable_thinking": False}
    model_kwargs: dict = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}
        logger.debug(f"[调试] 已开启 JSON 输出 | model={target_model}")

    # 5. 创建客户端并写入缓存
    logger.info(f"[提示] LLM 客户端初始化 | model={target_model} | json_mode={json_mode}")
    try:
        llm_client = ChatOpenAI(
            model=target_model,
            temperature=lm_config.llm_temperature or _DEFAULT_TEMPERATURE,
            api_key=lm_config.api_key,
            base_url=lm_config.base_url,
            extra_body=extra_body,
            model_kwargs=model_kwargs,
        )
    except LangChainException as exc:
        raise business_error(
            RuntimeError, "", "LLM 客户端初始化失败", model=target_model, error=exc
        ) from exc

    _llm_client_cache[cache_key] = llm_client
    logger.info(f"[提示] LLM 客户端就绪 | model={target_model} | json_mode={json_mode}")
    return llm_client
