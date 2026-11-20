"""
导入流程的 LangGraph 编排.

定义节点 边 与条件路由, 输出可执行对象 import_graph_app.
"""
from langgraph.graph import END, START, StateGraph

from app.constants.node_constants import (
    NODE_BGE_EMBEDDING,
    NODE_DOCUMENT_SPLIT,
    NODE_ENTRY,
    NODE_IMPORT_MILVUS,
    NODE_ITEM_NAME_RECOGNITION,
    NODE_MD_IMG,
    NODE_PDF_TO_MD,
)
from app.process.import_.agent.nodes.node_bge_embedding import node_bge_embedding
from app.process.import_.agent.nodes.node_document_split import node_document_split
from app.process.import_.agent.nodes.node_entry import node_entry
from app.process.import_.agent.nodes.node_import_milvus import node_import_milvus
from app.process.import_.agent.nodes.node_item_name_recognition import node_item_name_recognition
from app.process.import_.agent.nodes.node_md_img import node_md_img
from app.process.import_.agent.nodes.node_pdf_to_md import node_pdf_to_md
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger

# ---------------------------------------------------------------------------
# 建图与注册
# ---------------------------------------------------------------------------
# 1. 建图, 绑定全局状态
_import_builder = StateGraph(state_schema=ImportGraphState)

# 2. 注册节点
_import_builder.add_node(NODE_ENTRY, node_entry)
_import_builder.add_node(NODE_PDF_TO_MD, node_pdf_to_md)
_import_builder.add_node(NODE_MD_IMG, node_md_img)
_import_builder.add_node(NODE_DOCUMENT_SPLIT, node_document_split)
_import_builder.add_node(NODE_ITEM_NAME_RECOGNITION, node_item_name_recognition)
_import_builder.add_node(NODE_BGE_EMBEDDING, node_bge_embedding)
_import_builder.add_node(NODE_IMPORT_MILVUS, node_import_milvus)

# 3. 入口边
_import_builder.add_edge(START, NODE_ENTRY)


# ---------------------------------------------------------------------------
# 条件路由
# ---------------------------------------------------------------------------
def after_node_entry(state: ImportGraphState) -> str:
    """
    入口节点后的条件路由.

    Markdown 走图片增强, PDF 走格式转换, 其他类型直接结束.

    Args:
        state: 图全局状态.

    Returns:
        str: 下一节点名或 END.
    """
    task_id = state.get("task_id")
    file_title = state.get("file_title")

    if state.get("is_md_read_enabled"):
        logger.info(f"[提示] 路由 Markdown | task_id={task_id} | file={file_title}")
        return NODE_MD_IMG

    if state.get("is_pdf_read_enabled"):
        logger.info(f"[提示] 路由 PDF | task_id={task_id} | file={file_title}")
        return NODE_PDF_TO_MD

    logger.warning(
        f"[警告] 路由终止, 文件类型不支持 | task_id={task_id} "
        f"| is_md={state.get('is_md_read_enabled')} | is_pdf={state.get('is_pdf_read_enabled')}"
    )
    return END


# ---------------------------------------------------------------------------
# 边连接
# ---------------------------------------------------------------------------
_import_builder.add_conditional_edges(
    NODE_ENTRY,
    after_node_entry,
    {
        NODE_MD_IMG: NODE_MD_IMG,
        NODE_PDF_TO_MD: NODE_PDF_TO_MD,
        END: END,
    },
)

# PDF 转换完成后汇合到图片增强
_import_builder.add_edge(NODE_PDF_TO_MD, NODE_MD_IMG)

# 主流程: 图片增强 -> 切分 -> 主体识别 -> 向量化 -> 入库
_import_builder.add_edge(NODE_MD_IMG, NODE_DOCUMENT_SPLIT)
_import_builder.add_edge(NODE_DOCUMENT_SPLIT, NODE_ITEM_NAME_RECOGNITION)
_import_builder.add_edge(NODE_ITEM_NAME_RECOGNITION, NODE_BGE_EMBEDDING)
_import_builder.add_edge(NODE_BGE_EMBEDDING, NODE_IMPORT_MILVUS)
_import_builder.add_edge(NODE_IMPORT_MILVUS, END)


# ---------------------------------------------------------------------------
# 编译导出
# ---------------------------------------------------------------------------
import_graph_app = _import_builder.compile()
