"""
任务状态追踪工具模块。

基于内存字典维护单进程下各个任务 (task_id) 的运行中节点、已完成节点、
任务状态与结果数据。提供线程安全的状态读写、中文名映射以及 SSE 进度推送能力。
"""
from typing import Dict, List
from .sse_utils import push_to_session

# ---------------------------------------------------------------------------
# 内存态任务追踪 (单进程)
# ---------------------------------------------------------------------------
# key: task_id, value: 节点名列表 (原始英文/节点ID)
_tasks_running_list: Dict[str, List[str]] = {}
_tasks_done_list: Dict[str, List[str]] = {}

# key: task_id, value: status 字符串 (如 pending/processing/completed/failed)
_tasks_status: Dict[str, str] = {}

# key: task_id, value: 任务结果 (例如 query 的 answer)
_tasks_result: Dict[str, Dict[str, str]] = {}

# 任务状态常量定义
TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# 节点名 -> 中文名映射 (用于前端展示)
# 说明: 这里的 key 应与 LangGraph 的 add_node("xxx", ...) 中的节点名一致。
_NODE_NAME_TO_CN: Dict[str, str] = {
    "upload_file": "开始上传文件",
    "node_entry": "检查文件",
    "node_pdf_to_md": "PDF转Markdown",
    "node_md_img": "Markdown图片处理",
    "node_item_name_recognition": "主体名称识别",
    "node_document_split": "文档切分",
    "node_bge_embedding": "向量生成",
    "node_import_kg": "导入知识图谱",
    "node_import_milvus": "导入向量库",
    "__end__": "处理完成",
    "END": "处理完成",
    # --- Query 流程节点 (kb/process/query/main_graph.py) ---
    "node_item_name_confirm": "确认问题产品",
    "node_answer_output": "生成答案",
    "node_rerank": "重排序",
    "node_rrf": "倒排融合",
    "node_web_search_mcp": "网络搜索",
    "node_search_embedding": "切片搜索",
    "node_search_embedding_hyde": "切片搜索(假设性文档)",
    "node_multi_search": "多路搜索",
    "node_query_kg": "查询知识图谱",
    "node_join": "多路搜索合并",
}


# ---------------------------------------------------------------------------
# 内部辅助方法
# ---------------------------------------------------------------------------
def _ensure_task(task_id: str) -> None:
    """确保 task_id 对应的数据结构已初始化，避免键不存在导致的 KeyError。

    Args:
        task_id (str): 任务唯一标识。
    """
    if task_id not in _tasks_running_list:
        _tasks_running_list[task_id] = []
    if task_id not in _tasks_done_list:
        _tasks_done_list[task_id] = []
    if task_id not in _tasks_result:
        _tasks_result[task_id] = {}


def _to_cn(node_name: str) -> str:
    """将节点名转换为中文展示名；若无映射则返回原名。

    Args:
        node_name (str): 节点的英文 ID 名称。

    Returns:
        str: 对应的中文展示名称。
    """
    return _NODE_NAME_TO_CN.get(node_name, node_name)


# ---------------------------------------------------------------------------
# 任务状态追踪方法
# ---------------------------------------------------------------------------
def add_running_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """添加“正在运行”的节点任务。

    Args:
        task_id (str): 任务唯一标识。
        node_name (str): 节点名称 (节点ID)。
        is_stream (bool): 是否在状态变更后触发 SSE 推送。
    """
    _ensure_task(task_id)
    running = _tasks_running_list[task_id]
    # 避免重复追加
    if node_name not in running:
        running.append(node_name)

    if is_stream:
        task_push_queue(task_id)


def add_done_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """添加“已完成”的节点任务，并将同名的“正在运行”任务移除。

    Args:
        task_id (str): 任务唯一标识。
        node_name (str): 节点名称 (节点ID)。
        is_stream (bool): 是否在状态变更后触发 SSE 推送。
    """
    _ensure_task(task_id)

    # 从 running 中移除同名节点 (可能出现重复，移除所有)
    running = _tasks_running_list[task_id]
    _tasks_running_list[task_id] = [n for n in running if n != node_name]

    # 追加到 done (保持完成顺序)，避免重复
    done = _tasks_done_list[task_id]
    if node_name not in done:
        done.append(node_name)

    if is_stream:
        task_push_queue(task_id)


def set_task_result(task_id: str, key: str, value: str) -> None:
    """存储任务结果字段。

    Args:
        task_id (str): 任务唯一标识。
        key (str): 结果字段名，如 answer 或 error。
        value (str): 结果字段对应的值。
    """
    _ensure_task(task_id)
    _tasks_result[task_id][key] = value


def get_task_result(task_id: str, key: str, default: str = "") -> str:
    """获取任务结果字段。

    Args:
        task_id (str): 任务唯一标识。
        key (str): 结果字段名，如 answer 或 error。
        default (str): 若字段不存在时返回的默认值。

    Returns:
        str: 对应的任务结果内容。
    """
    _ensure_task(task_id)
    return _tasks_result.get(task_id, {}).get(key, default)


def get_task_status(task_id: str) -> str:
    """获取当前任务状态。

    Args:
        task_id (str): 任务唯一标识。

    Returns:
        str: 状态名称；如果未设置过则返回空字符串。
    """
    return _tasks_status.get(task_id, "")


def get_done_task_list(task_id: str) -> List[str]:
    """获取已完成节点列表 (中文展示)。

    Args:
        task_id (str): 任务唯一标识。

    Returns:
        List[str]: 已完成节点的中文名称列表。
    """
    _ensure_task(task_id)
    done = _tasks_done_list.get(task_id, [])
    return [_to_cn(n) for n in done]


def get_running_task_list(task_id: str) -> List[str]:
    """获取正在运行节点列表 (中文展示)。

    Args:
        task_id (str): 任务唯一标识。

    Returns:
        List[str]: 正在运行节点的中文名称列表。
    """
    _ensure_task(task_id)
    running = _tasks_running_list.get(task_id, [])
    return [_to_cn(n) for n in running]


def update_task_status(task_id: str, status_name: str, push_queue: bool = False) -> None:
    """更新任务状态。

    Args:
        task_id (str): 任务唯一标识。
        status_name (str): 状态名称字符串。
        push_queue (bool): 是否在状态更新后触发 SSE 推送。
    """
    _tasks_status[task_id] = status_name
    if push_queue:
        task_push_queue(task_id)


# ---------------------------------------------------------------------------
# SSE 推送与清理
# ---------------------------------------------------------------------------
def task_push_queue(task_id: str) -> None:
    """将当前任务进度打包并通过 SSE 推送给前端。

    推送的数据包含当前任务状态、已完成节点列表以及正在运行节点列表。

    Args:
        task_id (str): 任务唯一标识。
    """
    push_to_session(task_id, "progress", {
        "status": get_task_status(task_id),
        "done_list": get_done_task_list(task_id),
        "running_list": get_running_task_list(task_id),
    })


def clear_task(task_id: str) -> None:
    """清理指定任务的全部内存数据，释放资源。

    Args:
        task_id (str): 任务唯一标识。
    """
    _tasks_running_list.pop(task_id, None)
    _tasks_done_list.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)