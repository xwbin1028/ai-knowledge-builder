"""
Embedding 向量模型配置.

从 .env 读取 BGE-M3 的路径 名称 设备与精度, 装配为全局单例 embedding_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_bool, env_str


@dataclass
class EmbeddingConfig:
    """BGE-M3 向量模型配置项."""

    bge_m3_path: str     # 本地模型目录
    bge_m3: str          # 模型标识
    bge_device: str      # 运行设备, cpu 或 cuda
    bge_fp16: bool       # 是否启用半精度


embedding_config = EmbeddingConfig(
    bge_m3_path=env_str("BGE_M3_PATH"),
    bge_m3=env_str("BGE_M3"),
    bge_device=env_str("BGE_DEVICE"),
    bge_fp16=env_bool("BGE_FP16"),
)
