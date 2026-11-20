"""
任务进度追踪.

单进程内存态, 未加锁; 多实例部署需换成 Redis. 进度通过 SSE 推送给前端.
"""
from app.constants.node_constants import (
    NODE_ANSWER_OUTPUT,
    NODE_BGE_EMBEDDING,
    NODE_DOCUMENT_SPLIT,
    NODE_END,
    NODE_ENTRY,
    NODE_IMPORT_MILVUS,
    NODE_ITEM_NAME_CONFIRM,
    NODE_ITEM_NAME_RECOGNITION,
    NODE_JOIN,
    NODE_MD_IMG,
    NODE_MULTI_SEARCH,
    NODE_PDF_TO_MD,
    NODE_QUERY_KG,
    NODE_RERANK,
    NODE_RRF,
    NODE_SEARCH_EMBEDDING,
    NODE_SEARCH_EMBEDDING_HYDE,
    NODE_WEB_SEARCH_MCP,
)
from app.shared.utils.sse_utils import push_to_session

# ---------------------------------------------------------------------------
# 内存态任务数据
# ---------------------------------------------------------------------------
# key: task_id, value: 运行中的节点名
_tasks_running_list: dict[str, list[str]] = {}

# key: task_id, value: 已完成的节点名
_tasks_done_list: dict[str, list[str]] = {}

# key: task_id, value: 状态字符串
_tasks_status: dict[str, str] = {}

# key: task_id, value: 结果字段, 如 answer error
_tasks_result: dict[str, dict[str, str]] = {}

TASK_STATUS_PENDING = "pending"
TASK_STATUS_PROCESSING = "processing"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

# 节点名 -> 前端展示名, key 必须与 node_constants 一致
_NODE_NAME_TO_CN: dict[str, str] = {
    "upload_file": "开始上传文件",
    NODE_ENTRY: "检查文件",
    NODE_PDF_TO_MD: "PDF 转 Markdown",
    NODE_MD_IMG: "Markdown 图片处理",
    NODE_ITEM_NAME_RECOGNITION: "主体名称识别",
    NODE_DOCUMENT_SPLIT: "文档切分",
    NODE_BGE_EMBEDDING: "向量生成",
    NODE_IMPORT_MILVUS: "导入向量库",
    NODE_END: "处理完成",
    "END": "处理完成",
    # 查询流程, 待实现
    NODE_ITEM_NAME_CONFIRM: "确认问题产品",
    NODE_ANSWER_OUTPUT: "生成答案",
    NODE_RERANK: "重排序",
    NODE_RRF: "倒排融合",
    NODE_WEB_SEARCH_MCP: "网络搜索",
    NODE_SEARCH_EMBEDDING: "切片搜索",
    NODE_SEARCH_EMBEDDING_HYDE: "切片搜索, 假设性文档",
    NODE_MULTI_SEARCH: "多路搜索",
    NODE_QUERY_KG: "查询知识图谱",
    NODE_JOIN: "多路搜索合并",
}


# ---------------------------------------------------------------------------
# 内部方法
# ---------------------------------------------------------------------------
def _ensure_task(task_id: str) -> None:
    """确保 task_id 的数据结构存在, 避免 KeyError."""
    _tasks_running_list.setdefault(task_id, [])
    _tasks_done_list.setdefault(task_id, [])
    _tasks_result.setdefault(task_id, {})


def _to_cn(node_name: str) -> str:
    """节点名转前端展示名, 无映射时返回原名."""
    return _NODE_NAME_TO_CN.get(node_name, node_name)


# ---------------------------------------------------------------------------
# 状态写入
# ---------------------------------------------------------------------------
def add_running_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """
    上报运行中的节点.

    Args:
        task_id: 任务 ID.
        node_name: 节点名.
        is_stream: 是否推送 SSE.
    """
    _ensure_task(task_id)
    running = _tasks_running_list[task_id]
    if node_name not in running:
        running.append(node_name)

    if is_stream:
        push_task_progress(task_id)


def add_done_task(task_id: str, node_name: str, is_stream: bool = False) -> None:
    """
    上报已完成的节点, 并从运行中移除同名节点.

    Args:
        task_id: 任务 ID.
        node_name: 节点名.
        is_stream: 是否推送 SSE.
    """
    _ensure_task(task_id)

    running = _tasks_running_list[task_id]
    _tasks_running_list[task_id] = [name for name in running if name != node_name]

    done = _tasks_done_list[task_id]
    if node_name not in done:
        done.append(node_name)

    if is_stream:
        push_task_progress(task_id)


def set_task_result(task_id: str, key: str, value: str) -> None:
    """
    写入任务结果字段.

    Args:
        task_id: 任务 ID.
        key: 字段名, 如 answer.
        value: 字段值.
    """
    _ensure_task(task_id)
    _tasks_result[task_id][key] = value


def update_task_status(task_id: str, status_name: str, push_queue: bool = False) -> None:
    """
    更新任务状态.

    Args:
        task_id: 任务 ID.
        status_name: 状态名, 取 TASK_STATUS_* 常量.
        push_queue: 是否推送 SSE.
    """
    _tasks_status[task_id] = status_name
    if push_queue:
        push_task_progress(task_id)


# ---------------------------------------------------------------------------
# 状态读取
# ---------------------------------------------------------------------------
def get_task_result(task_id: str, key: str, default: str = "") -> str:
    """
    读取任务结果字段.

    Args:
        task_id: 任务 ID.
        key: 字段名.
        default: 缺失时的默认值.

    Returns:
        str: 字段值.
    """
    _ensure_task(task_id)
    return _tasks_result.get(task_id, {}).get(key, default)


def get_task_status(task_id: str) -> str:
    """
    读取任务状态.

    Args:
        task_id: 任务 ID.

    Returns:
        str: 状态名, 未设置时为空串.
    """
    return _tasks_status.get(task_id, "")


def get_done_task_list(task_id: str) -> list[str]:
    """
    读取已完成节点, 返回中文展示名.

    Args:
        task_id: 任务 ID.

    Returns:
        list[str]: 已完成节点名.
    """
    _ensure_task(task_id)
    return [_to_cn(name) for name in _tasks_done_list.get(task_id, [])]


def get_running_task_list(task_id: str) -> list[str]:
    """
    读取运行中节点, 返回中文展示名.

    Args:
        task_id: 任务 ID.

    Returns:
        list[str]: 运行中节点名.
    """
    _ensure_task(task_id)
    return [_to_cn(name) for name in _tasks_running_list.get(task_id, [])]


# ---------------------------------------------------------------------------
# 推送与清理
# ---------------------------------------------------------------------------
def push_task_progress(task_id: str) -> None:
    """
    推送一次任务进度.

    Args:
        task_id: 任务 ID.
    """
    push_to_session(task_id, "progress", {
        "status": get_task_status(task_id),
        "done_list": get_done_task_list(task_id),
        "running_list": get_running_task_list(task_id),
    })


def clear_task(task_id: str) -> None:
    """
    清理任务的全部内存数据.

    Args:
        task_id: 任务 ID.
    """
    _tasks_running_list.pop(task_id, None)
    _tasks_done_list.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)
