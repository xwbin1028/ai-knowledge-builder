"""
模型服务提供者.

职责: 统一对外暴露对话 视觉 向量与重排入口.
边界: 不负责业务编排, 模型配置统一来自 infra_config.
"""
from pathlib import Path
from typing import Any

from app.infra.config.providers import infra_config
from app.shared.model.lm_utils import get_llm_client
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import logger

# BGE-M3 模型, 首次向量化时加载
_bge_m3_model: Any = None


def _get_bge_m3_model() -> Any:
    """
    获取或加载 BGE-M3 模型.

    业务逻辑:
        1. 已加载则直接返回
        2. 解析本地路径或模型名
        3. 延迟导入 FlagEmbedding 并加载模型
        4. 缓存后返回

    Returns:
        BGEM3FlagModel: 全局复用模型.

    Raises:
        ValueError: 本地路径不存在或模型未配置.
        RuntimeError: 模型加载失败.
    """
    global _bge_m3_model

    # 1. 已加载则直接返回
    if _bge_m3_model is not None:
        return _bge_m3_model

    # 2. 解析本地路径或模型名
    local_path: str = infra_config.embedding.bge_m3_path
    model_name: str = infra_config.embedding.bge_m3
    if local_path:
        if not Path(local_path).exists():
            raise business_error(ValueError, "", "BGE-M3 本地路径不存在", path=local_path)
        model_path = local_path
    else:
        model_path = model_name
    if not model_path:
        raise business_error(ValueError, "", "BGE-M3 模型未配置", field="BGE_M3_PATH")

    # 3. 延迟导入 FlagEmbedding 并加载模型
    from FlagEmbedding import BGEM3FlagModel

    try:
        _bge_m3_model = BGEM3FlagModel(
            model_name_or_path=model_path,
            use_fp16=infra_config.embedding.bge_fp16,
            devices=infra_config.embedding.bge_device or None,
        )
    except Exception as exc:
        raise business_error(
            RuntimeError, "", "BGE-M3 模型加载失败", model=model_path, error=exc
        ) from exc

    # 4. 缓存后返回
    logger.info(
        f"[提示] BGE-M3 模型就绪 | model={model_path} "
        f"| device={infra_config.embedding.bge_device}"
    )
    return _bge_m3_model


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

    def embed_texts(self, texts: list[str]) -> dict[str, list[Any]]:
        """
        生成稠密与稀疏向量.

        业务逻辑:
            1. 校验文本非空
            2. 加载 BGE-M3 模型
            3. 编码文本
            4. 转成普通 list 与 dict 返回

        Args:
            texts: 待向量化文本.

        Returns:
            dict[str, list[Any]]: dense 为向量列表, sparse 为 token id 到权重的字典列表.

        Raises:
            ValueError: 文本为空.
            RuntimeError: 模型加载或编码失败.
        """
        # 1. 校验文本非空
        if not texts:
            raise business_error(ValueError, "", "待向量化文本为空", field="texts")

        # 2. 加载 BGE-M3 模型
        model = _get_bge_m3_model()

        # 3. 编码文本
        try:
            result = model.encode(
                sentences=texts,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
        except Exception as exc:
            raise business_error(
                RuntimeError, "", "BGE-M3 向量生成失败", count=len(texts), error=exc
            ) from exc

        # 4. 转成普通 list 与 dict 返回
        dense_list: list[list[float]] = [
            vector.tolist() if hasattr(vector, "tolist") else list(vector)
            for vector in result["dense_vecs"]
        ]
        sparse_list: list[dict[int, float]] = [
            {int(token): float(weight) for token, weight in weights.items()}
            for weights in result["lexical_weights"]
        ]
        logger.info(
            f"[提示] BGE-M3 向量生成完成 | count={len(texts)} "
            f"| dim={len(dense_list[0]) if dense_list else 0}"
        )
        return {"dense": dense_list, "sparse": sparse_list}

    def rerank(self, model: str | None = None):
        """获取重排模型客户端, 待实现."""
        raise NotImplementedError("rerank provider 未实现, 见 reranker_config")


llm_provider = LLMProvider()
