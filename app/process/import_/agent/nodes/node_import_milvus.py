"""
图节点：向量库导入节点。

调用入库服务，将已生成向量的切片数据批量写入 Milvus 数据库，
并在执行前后更新任务追踪状态与结构化日志。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_running_task, add_done_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.index_service import index_chunks


# ---------------------------------------------------------------------------
# 节点定义
# ---------------------------------------------------------------------------
@node_log("node_import_milvus")
def node_import_milvus(state: ImportGraphState) -> ImportGraphState:
    """
    节点：导入向量库。

    核心任务：将处理好的向量数据写入 Milvus 数据库。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_import_milvus")
    state = index_chunks(state)
    add_done_task(state["task_id"], "node_import_milvus")
    return state
