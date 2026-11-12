"""
图节点：PDF 转 Markdown 节点。

调用 PDF 解析服务将非结构化 PDF 转换为结构化 Markdown，
并通过装饰器自动记录节点运行日志与任务状态。
"""
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.pdf_parse_service import parse_pdf_to_markdown


@node_log("node_pdf_to_md")
def node_pdf_to_md(state: ImportGraphState) -> ImportGraphState:
    """
    节点：PDF 转 Markdown。

    核心任务：将 PDF 非结构化数据转换为 Markdown 结构化数据。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    add_running_task(state["task_id"], "node_pdf_to_md")
    state = parse_pdf_to_markdown(state)
    add_done_task(state["task_id"], "node_pdf_to_md")
    return state