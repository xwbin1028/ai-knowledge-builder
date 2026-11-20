"""
Milvus 入库服务.

准备集合与索引, 按 item_name 清理旧数据, 批量写入切片并回写 chunk_id.
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger


def index_chunks(state: ImportGraphState) -> ImportGraphState:
    """
    写入向量库.

    待实现: 准备集合 -> 按 item_name 删旧 -> 批量插入 -> 回写 chunk_id.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 原样返回, 当前未实现.
    """
    # TODO: 待实现, 需要 Milvus 连接与集合 Schema
    task_id: str = state.get("task_id", "")
    logger.warning(f"[警告] task_id={task_id} | 向量入库未实现, 跳过")
    return state
