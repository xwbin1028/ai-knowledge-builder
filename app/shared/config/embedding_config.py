"""
Embedding 配置模块。
负责从环境变量中读取 BGE 向量模型的路径 运行设备等参数，
并将其封装为强类型的全局单例实例 embedding_config 供业务代码直接调用。
"""
from dataclasses import dataclass
from app.shared.config.common import env_bool, env_str


# ---------------------------------------------------------------------------
# 配置模型定义
# ---------------------------------------------------------------------------
@dataclass
class EmbeddingConfig:
    """
    BGE 向量模型配置项的数据类。

    Attributes:
        bge_m3_path (str): 模型在本地磁盘的绝对路径或相对路径。
        bge_m3 (str): 模型名称。
        bge_device (str): 模型运行的硬件设备。
        bge_fp16 (bool): 是否启用半精度浮点数 FP16 加速。
    """
    bge_m3_path: str
    bge_m3: str
    bge_device: str
    bge_fp16: bool


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 使用 common.py 全局环境变量工具封装简化代码
embedding_config = EmbeddingConfig(
    bge_m3_path=env_str("BGE_M3_PATH"),
    bge_m3=env_str("BGE_M3"),
    bge_device=env_str("BGE_DEVICE"),
    bge_fp16=env_bool("BGE_FP16"),
)
