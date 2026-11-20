"""
节点: 主体名称识别.

读取 state 的 chunks, 调用 LLM 识别主体名称, 回写 item_name.
"""
from app.constants.node_constants import NODE_ITEM_NAME_RECOGNITION
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.item_name_service import recognize_and_index_item_name
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_ITEM_NAME_RECOGNITION)
def node_item_name_recognition(state: ImportGraphState) -> ImportGraphState:
    """
    节点: 主体名称识别.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 item_name 的状态.
    """
    add_running_task(state["task_id"], NODE_ITEM_NAME_RECOGNITION)
    state = recognize_and_index_item_name(state)
    add_done_task(state["task_id"], NODE_ITEM_NAME_RECOGNITION)
    return state
