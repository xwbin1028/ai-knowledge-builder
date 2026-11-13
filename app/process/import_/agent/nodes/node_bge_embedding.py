"""
图节点：BGE-M3 向量化节点。

调用向量化服务，将文档切片转换为稠密与稀疏向量表示，
并在执行前后更新任务追踪状态与结构化日志。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_running_task, add_done_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.embedding_service import generate_chunk_embeddings


# ---------------------------------------------------------------------------
# 节点定义
# ---------------------------------------------------------------------------
@node_log("node_bge_embedding")
def node_bge_embedding(state: ImportGraphState) -> ImportGraphState:
    """
    节点：向量化。

    核心任务：使用 BGE-M3 模型将文本转换为向量。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_bge_embedding")
    state = generate_chunk_embeddings(state)
    add_done_task(state["task_id"], "node_bge_embedding")
    return state
