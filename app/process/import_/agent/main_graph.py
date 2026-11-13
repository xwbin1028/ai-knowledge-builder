"""
文档导入 LangGraph 图构建模块。

负责编排文档导入 RAG 流水线的完整拓扑结构。定义了所有处理节点
以及节点间的流转规则，并通过条件路由函数决定不同类型文件的处理走向。
最终通过 compile 方法将图实例化为可执行的 Runnable 对象。
"""
from langgraph.graph import StateGraph, START, END
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger
from app.process.import_.agent.nodes.node_entry import node_entry
from app.process.import_.agent.nodes.node_pdf_to_md import node_pdf_to_md
from app.process.import_.agent.nodes.node_md_img import node_md_img
from app.process.import_.agent.nodes.node_document_split import node_document_split
from app.process.import_.agent.nodes.node_item_name_recognition import node_item_name_recognition
from app.process.import_.agent.nodes.node_bge_embedding import node_bge_embedding
from app.process.import_.agent.nodes.node_import_milvus import node_import_milvus

# ---------------------------------------------------------------------------
# 图构建与节点注册
# ---------------------------------------------------------------------------
# 1. 创建图的构建对象，指定全局状态的数据模型
import_builder = StateGraph(state_schema=ImportGraphState)

# 2. 添加所有业务处理节点
import_builder.add_node("node_entry", node_entry)
import_builder.add_node("node_pdf_to_md", node_pdf_to_md)
import_builder.add_node("node_md_img", node_md_img)
import_builder.add_node("node_document_split", node_document_split)
import_builder.add_node("node_item_name_recognition", node_item_name_recognition)
import_builder.add_node("node_bge_embedding", node_bge_embedding)
import_builder.add_node("node_import_milvus", node_import_milvus)

# 3. 添加起始边，图启动后首先进入文件识别节点
import_builder.add_edge(START, "node_entry")


# ---------------------------------------------------------------------------
# 条件路由函数
# ---------------------------------------------------------------------------
def after_node_entry(state: ImportGraphState) -> str:
    """
    入口节点后的条件路由函数。

    根据 node_entry 节点解析出的文件类型标识，决定下一步流向：
        - Markdown 文件：直接进入图片意图识别节点 node_md_img。
        - PDF 文件：先进入格式转换节点 node_pdf_to_md。
        - 其他类型：直接结束流程。

    Args:
        state (ImportGraphState): 图全局状态，包含文件类型的布尔标识。

    Returns:
        str: 下一个要执行的节点名称，或 END 结束标志。
    """
    if state.get("is_md_read_enabled"):
        # 使用具名占位符记录日志，提升性能与可读性
        logger.info(
            "Markdown 文件路由分发成功，即将进入图片意图识别 - task_id: {task_id}, file: {file_title}",
            task_id=state.get("task_id"),
            file_title=state.get("file_title")
        )
        return "node_md_img"

    elif state.get("is_pdf_read_enabled"):
        # 使用具名占位符记录日志，提升性能与可读性
        logger.info(
            "PDF 文件路由分发成功，即将进入解析转换流程 - task_id: {task_id}, file: {file_title}",
            task_id=state.get("task_id"),
            file_title=state.get("file_title")
        )
        return "node_pdf_to_md"

    else:
        # 异常分支：记录完整的类型标志位，便于排查未知格式拦截问题
        logger.warning(
            "文件路由终止：不支持的文件类型 - task_id: {task_id}, is_md_flag: {is_md_flag}, is_pdf_flag: {is_pdf_flag}",
            task_id=state.get("task_id"),
            is_md_flag=state.get("is_md_read_enabled"),
            is_pdf_flag=state.get("is_pdf_read_enabled")
        )
        return END


# ---------------------------------------------------------------------------
# 条件边连接
# ---------------------------------------------------------------------------
# 将 node_entry 节点的输出路由到不同的目标节点
# 映射字典的 key 为路由函数返回值，value 为目标节点名称
import_builder.add_conditional_edges(
    "node_entry",
    after_node_entry,
    {
        "node_md_img": "node_md_img",
        "node_pdf_to_md": "node_pdf_to_md",
        END: END
    }
)


# ---------------------------------------------------------------------------
# 固定边连接 (线性流水线装配)
# ---------------------------------------------------------------------------
# PDF 解析完成后，统一汇合到 Markdown 图片处理节点
import_builder.add_edge("node_pdf_to_md", "node_md_img")

# 构造从图片处理到向量入库的线性主流程
import_builder.add_edge("node_md_img", "node_document_split")
import_builder.add_edge("node_document_split", "node_item_name_recognition")
import_builder.add_edge("node_item_name_recognition", "node_bge_embedding")
import_builder.add_edge("node_bge_embedding", "node_import_milvus")

# 数据入库完成后，结束整个图流程
import_builder.add_edge("node_import_milvus", END)


# ---------------------------------------------------------------------------
# 图编译与导出
# ---------------------------------------------------------------------------
import_graph_app = import_builder.compile()
