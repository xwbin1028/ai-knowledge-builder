"""
Reranker 重排模型配置.

从 .env 读取 BGE 重排模型的路径 设备与精度, 装配为全局单例 reranker_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_bool, env_str


@dataclass
class RerankerConfig:
    """BGE Reranker 配置项."""

    bge_reranker_large: str   # 模型目录或标识
    bge_reranker_device: str  # 运行设备, cpu 或 cuda
    bge_reranker_fp16: bool   # 是否启用半精度


reranker_config = RerankerConfig(
    bge_reranker_large=env_str("BGE_RERANKER_LARGE"),
    bge_reranker_device=env_str("BGE_RERANKER_DEVICE"),
    bge_reranker_fp16=env_bool("BGE_RERANKER_FP16"),
)
