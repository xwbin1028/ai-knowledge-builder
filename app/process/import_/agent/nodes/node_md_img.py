"""
图节点：Markdown 图片处理节点。

接收图全局状态，调用底层的 Markdown 图片增强服务处理图片资源，
并在执行前后更新任务追踪状态与结构化日志。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.markdown_image_service import enrich_markdown_image


# ---------------------------------------------------------------------------
# 节点定义
# ---------------------------------------------------------------------------
@node_log("node_md_img")
def node_md_img(state: ImportGraphState) -> ImportGraphState:
    """
    节点：图片处理。

    核心任务：处理 Markdown 中的图片资源。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_md_img")
    state = enrich_markdown_image(state)
    add_done_task(state["task_id"], "node_md_img")
    return state
