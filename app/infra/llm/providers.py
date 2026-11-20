"""
模型服务提供者.

统一对外暴露对话 视觉 向量 重排四类客户端, 业务侧不直接实例化模型.
"""
from app.infra.config.providers import infra_config
from app.shared.model.lm_utils import get_llm_client


class LLMProvider:
    """模型服务入口, 全局单例 llm_provider."""

    def chat(self, model: str | None = None, json_mode: bool = False):
        """
        获取对话模型客户端.

        Args:
            model: 模型名, 为空时用 lm_config.llm_model.
            json_mode: 是否开启 JSON 输出.

        Returns:
            ChatOpenAI: 对话客户端.
        """
        return get_llm_client(model=model, json_mode=json_mode)

    def vision_chat(self, model: str | None = None):
        """
        获取视觉模型客户端.

        Args:
            model: 视觉模型名, 为空时用 lm_config.vl_model.

        Returns:
            ChatOpenAI: 视觉客户端.
        """
        return get_llm_client(model=model or infra_config.llm.vl_model, json_mode=False)

    def embedding(self, model: str | None = None):
        """获取向量模型客户端, 待实现."""
        raise NotImplementedError("embedding provider 未实现, 见 embedding_config")

    def rerank(self, model: str | None = None):
        """获取重排模型客户端, 待实现."""
        raise NotImplementedError("rerank provider 未实现, 见 reranker_config")


llm_provider = LLMProvider()
