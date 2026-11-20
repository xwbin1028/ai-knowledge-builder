"""
文档切分服务.

按标题层级与长度把 md 正文切分为检索友好的 chunks.
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger


def split_document(state: ImportGraphState) -> ImportGraphState:
    """
    切分文档.

    待实现: 标题粗切 -> 超长细切 -> 构造 chunks -> 回写 state.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 原样返回, 当前未实现.
    """
    # TODO: 待实现, 需要切分参数与标题规则
    task_id: str = state.get("task_id", "")
    logger.warning(f"[警告] task_id={task_id} | 文档切分未实现, 跳过")
    return state
