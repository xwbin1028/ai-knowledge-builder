"""
Reranker 配置模块。
负责从环境变量中读取 BGE 重排模型的路径 运行设备等参数，
并将其封装为强类型的全局单例实例 reranker_config 供业务代码直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_bool, env_str


# ---------------------------------------------------------------------------
# 配置模型定义
# ---------------------------------------------------------------------------
@dataclass
class RerankerConfig:
    """
    BGE Reranker 重排模型配置项的数据类。

    Attributes:
        bge_reranker_large (str): 重排模型的名称或路径标识。
        bge_reranker_device (str): 模型运行的硬件设备，如 cpu 或 cuda。
        bge_reranker_fp16 (bool): 是否启用半精度浮点数 FP16 加速。
    """
    bge_reranker_large: str
    bge_reranker_device: str
    bge_reranker_fp16: bool


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
reranker_config = RerankerConfig(
    bge_reranker_large=env_str("BGE_RERANKER_LARGE"),
    bge_reranker_device=env_str("BGE_RERANKER_DEVICE"),
    bge_reranker_fp16=env_bool("BGE_RERANKER_FP16"),
)
