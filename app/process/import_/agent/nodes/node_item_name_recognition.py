"""
图节点：主体名称识别节点。

调用主体识别服务，基于文档切片构造上下文并识别核心实体名称，
并在执行前后更新任务追踪状态与结构化日志。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.item_name_service import recognize_and_index_item_name


# ---------------------------------------------------------------------------
# 节点定义
# ---------------------------------------------------------------------------
@node_log("node_item_name_recognition")
def node_item_name_recognition(state: ImportGraphState) -> ImportGraphState:
    """
    节点：主体识别。

    核心任务：识别文档核心描述的物品或商品名称。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_item_name_recognition")
    state = recognize_and_index_item_name(state)
    add_done_task(state["task_id"], "node_item_name_recognition")
    return state
