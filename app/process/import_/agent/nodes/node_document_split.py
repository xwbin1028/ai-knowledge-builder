"""
图节点：文档切分节点。

调用文档切分服务，将长文档按语义或结构切分为适合检索的文本块，
并在执行前后更新任务追踪状态与结构化日志。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.split_document import split_document


# ---------------------------------------------------------------------------
# 节点定义
# ---------------------------------------------------------------------------
@node_log("node_document_split")
def node_document_split(state: ImportGraphState) -> ImportGraphState:
    """
    节点：文档切分。

    核心任务：长文档切分成小的 chunks 以便检索。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_document_split")
    state = split_document(state)
    add_done_task(state["task_id"], "node_document_split")
    return state
