"""
节点: BGE-M3 向量化.

读取 state 的 chunks, 生成稠密与稀疏向量, 回写 embeddings_content.
"""
from app.constants.node_constants import NODE_BGE_EMBEDDING
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.embedding_service import generate_chunk_embeddings
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_BGE_EMBEDDING)
def node_bge_embedding(state: ImportGraphState) -> ImportGraphState:
    """
    节点: BGE-M3 向量化.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 embeddings_content 的状态.
    """
    add_running_task(state["task_id"], NODE_BGE_EMBEDDING)
    state = generate_chunk_embeddings(state)
    add_done_task(state["task_id"], NODE_BGE_EMBEDDING)
    return state
