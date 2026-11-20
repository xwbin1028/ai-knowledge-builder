"""
节点: 向量入库.

读取 state 的 chunks 与 embeddings, 写入 Milvus, 回写 chunk_id.
"""
from app.constants.node_constants import NODE_IMPORT_MILVUS
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.index_service import index_chunks
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_IMPORT_MILVUS)
def node_import_milvus(state: ImportGraphState) -> ImportGraphState:
    """
    节点: 向量入库.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入入库结果的状态.
    """
    add_running_task(state["task_id"], NODE_IMPORT_MILVUS)
    state = index_chunks(state)
    add_done_task(state["task_id"], NODE_IMPORT_MILVUS)
    return state
