"""
导入流程状态.

ImportGraphState 定义图内流转的全部字段, 默认模板与工厂方法保证任务间隔离.
"""
import copy
from typing import Any, TypedDict


class ImportGraphState(TypedDict):
    """导入流程状态, 字段只增不改名."""

    task_id: str                        # 任务 ID
    local_file_path: str                # 输入文件路径
    local_file_dir: str                 # 输出目录
    is_md_read_enabled: bool            # 是否走 Markdown 分支
    is_pdf_read_enabled: bool           # 是否走 PDF 分支
    md_path: str                        # md 文件路径
    pdf_path: str                       # pdf 文件路径
    md_content: str                     # md 正文
    item_name: str                      # 主体名称
    file_title: str                     # 文件标题
    chunks: list[dict[str, Any]]        # 文本切片
    embeddings: list[dict[str, Any]]    # 向量结果


GRAPH_DEFAULT_STATE: ImportGraphState = {
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
    创建带初始值的新状态.

    深拷贝默认模板, 避免任务间共享可变对象.

    Args:
        **kwargs: 需要覆盖的字段.

    Returns:
        ImportGraphState: 新状态.
    """
    new_state: ImportGraphState = copy.deepcopy(GRAPH_DEFAULT_STATE)
    new_state.update(kwargs)
    return new_state


def get_default_state() -> ImportGraphState:
    """
    创建完全默认的状态.

    Returns:
        ImportGraphState: 新状态.
    """
    return create_default_state()
