"""
节点: 文档切分.

读取 state 的 md_content, 按标题与长度切分, 回写 chunks.
"""
from app.constants.node_constants import NODE_DOCUMENT_SPLIT
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.split_document import split_document
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_DOCUMENT_SPLIT)
def node_document_split(state: ImportGraphState) -> ImportGraphState:
    """
    节点: 文档切分.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 chunks 的状态.
    """
    add_running_task(state["task_id"], NODE_DOCUMENT_SPLIT)
    state = split_document(state)
    add_done_task(state["task_id"], NODE_DOCUMENT_SPLIT)
    return state
