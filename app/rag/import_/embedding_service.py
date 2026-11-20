"""
向量化服务.

读取 chunks, 调 BGE-M3 生成稠密与稀疏向量, 回写 embeddings.
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger


def generate_chunk_embeddings(state: ImportGraphState) -> ImportGraphState:
    """
    生成切片向量.

    待实现: 读取 chunks -> BGE-M3 生成 dense 与 sparse -> 回写 embeddings.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 原样返回, 当前未实现.
    """
    # TODO: 待实现, 需要加载本地 BGE-M3 模型
    task_id: str = state.get("task_id", "")
    logger.warning(f"[警告] task_id={task_id} | 向量化未实现, 跳过")
    return state
