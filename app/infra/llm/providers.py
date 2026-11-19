from app.shared.model.lm_utils import get_llm_client
from app.infra.config.providers import infra_config


class LLMProvider:
    """大模型服务提供者，用于统一获取不同模态的 LLM 客户端。"""

    def chat(self, model: str | None = None, json_mode: bool = False):
        """
        获取通用对话模型客户端（适用于文本、代码等场景）。

        :param model: 指定的模型名称。若为 None，则由底层逻辑决定默认模型。
        :param json_mode: 是否开启 JSON 强制输出模式。
        :return: 初始化的 LLM 客户端实例。
        """
        return get_llm_client(model=model, json_mode=json_mode)

    def vision_chat(self, model: str | None = None):
        """
        获取视觉理解模型客户端（适用于图像、视频等场景）。

        :param model: 指定的视觉模型名称。若为 None，则读取配置中的默认视觉模型。
        :return: 初始化的视觉 LLM 客户端实例。
        """
        if not model:
            # 注意：原代码为 lv_model，常规缩写多为 vl_model (Vision-Language) 或 vision_model
            model = infra_config.llm.lv_model
        return get_llm_client(model=model, json_mode=False)

    # ---------------------------------------------------------
    # 待实现的模型接口
    # ---------------------------------------------------------

    def embedding(self, model: str | None = None):
        """获取嵌入式模型客户端（待实现）。"""
        raise NotImplementedError("Embedding model provider is not implemented yet.")

    def rerank(self, model: str | None = None):
        """获取重排序模型客户端（待实现）。"""
        raise NotImplementedError("Rerank model provider is not implemented yet.")


# 单例实例化，保持全局唯一
llm_provider = LLMProvider()
