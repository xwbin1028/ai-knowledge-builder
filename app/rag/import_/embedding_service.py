"""
向量化服务模块。

纯函数服务，读取文档切片并调用 BGE-M3 模型生成稠密与稀疏向量，
将向量结果补充回切片数据中，为后续混合检索提供基础。
"""
from app.process.import_.agent.state import ImportGraphState


def generate_chunk_embeddings(state: ImportGraphState) -> ImportGraphState:
    """
    向量化服务。

    执行步骤：
        1. 读取 chunks。
        2. 生成 dense_vector 与 sparse_vector。
        3. 将向量结果补充回 chunks。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state
