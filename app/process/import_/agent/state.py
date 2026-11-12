"""
图状态定义模块。
定义基于 TypedDict 的图状态模型 ImportGraphState 及其默认状态模板，
提供状态实例的安全创建方法，确保流转过程中数据的类型安全与对象隔离。
"""
from typing import TypedDict, Any
import copy


# ---------------------------------------------------------------------------
# 状态模型定义
# ---------------------------------------------------------------------------
class ImportGraphState(TypedDict):
    """
    图的状态定义，包含所有节点生产和消费的数据字段。

    使用 TypedDict 可以提供 IDE 自动补全和静态类型检查。
    访问方式支持字典语法如 state['task_id'] 或 state.get('task_id')。

    Attributes:
        task_id (str): 任务唯一标识。
        local_file_path (str): 输入文件的绝对或相对路径。
        local_file_dir (str): 输出文件夹的路径。
        is_md_read_enabled (bool): 是否启用 Markdown 文件解析。
        is_pdf_read_enabled (bool): 是否启用 PDF 文件解析。
        md_path (str): 解析后生成的 Markdown 文件存储路径。
        pdf_path (str): 解析后生成的 PDF 文件存储路径。
        md_content (str): Markdown 文件的具体文本内容。
        item_name (str): 文件主体的唯一标识名称。
        file_title (str): 文件标题。
        chunks (list[dict[str, Any]]): 文本切片内容列表。
        embeddings (list[dict[str, Any]]): 向量化后的切片内容列表。
    """
    task_id: str
    local_file_path: str
    local_file_dir: str
    is_md_read_enabled: bool
    is_pdf_read_enabled: bool
    md_path: str
    pdf_path: str
    md_content: str
    item_name: str
    file_title: str
    chunks: list[dict[str, Any]]
    embeddings: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# 默认模板与工厂方法
# ---------------------------------------------------------------------------
graph_default_state: ImportGraphState = {
    "task_id": "",
    "local_file_path": "",
    "local_file_dir": "",
    "is_md_read_enabled": False,
    "is_pdf_read_enabled": False,
    "md_path": "",
    "pdf_path": "",
    "md_content": "",
    "item_name": "",
    "file_title": "",
    "chunks": [],
    "embeddings": [],
}


def create_default_state(**kwargs) -> ImportGraphState:
    """
    创建带有自定义初始值的全新状态对象。
    通过深拷贝默认模板防止不同任务间的数据污染，并允许通过 kwargs 覆盖默认字段。

    Args:
        **kwargs: 需要覆盖的初始状态键值对。

    Returns:
        ImportGraphState: 初始化完成的状态字典对象。
    """
    new_graph_state: ImportGraphState = copy.deepcopy(graph_default_state)
    new_graph_state.update(kwargs)
    return new_graph_state


def get_default_state() -> ImportGraphState:
    """
    获取一个完全干净的默认状态对象。

    Returns:
        ImportGraphState: 默认初始化的状态字典对象。
    """
    new_graph_state: ImportGraphState = copy.deepcopy(graph_default_state)
    return new_graph_state
