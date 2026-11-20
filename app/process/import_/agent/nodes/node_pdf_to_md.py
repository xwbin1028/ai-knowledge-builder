"""
节点: PDF 转 Markdown.

读取 state 的 pdf_path, 调用 MinerU 解析, 回写 md_path.
"""
from app.constants.node_constants import NODE_PDF_TO_MD
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.pdf_parse_service import parse_pdf_to_markdown
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_PDF_TO_MD)
def node_pdf_to_md(state: ImportGraphState) -> ImportGraphState:
    """
    节点: PDF 转 Markdown.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 md_path 的状态.
    """
    add_running_task(state["task_id"], NODE_PDF_TO_MD)
    state = parse_pdf_to_markdown(state)
    add_done_task(state["task_id"], NODE_PDF_TO_MD)
    return state
