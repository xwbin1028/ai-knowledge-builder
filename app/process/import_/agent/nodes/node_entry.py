"""
节点: 入口识别.

读取 state 的 local_file_path, 校验并识别类型, 回写分支标志.
"""
from app.constants.node_constants import NODE_ENTRY
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.entry_service import resolve_input_file
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_ENTRY)
def node_entry(state: ImportGraphState) -> ImportGraphState:
    """
    节点: 入口识别.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入类型标志的状态.
    """
    add_running_task(state["task_id"], NODE_ENTRY)
    state = resolve_input_file(state)
    add_done_task(state["task_id"], NODE_ENTRY)
    return state
