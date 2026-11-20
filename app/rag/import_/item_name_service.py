"""
主体名称识别服务.

基于 chunks 构造上下文, 调 LLM 识别 item_name, 回填状态与切片并写主题索引.
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger


def recognize_and_index_item_name(state: ImportGraphState) -> ImportGraphState:
    """
    识别主体名称并写入索引.

    待实现: chunks 构造上下文 -> LLM 识别 item_name -> 回填 -> 写主题索引.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 原样返回, 当前未实现.
    """
    # TODO: 待实现, 需要 item_name_recognition 提示词与 LLM 客户端
    task_id: str = state.get("task_id", "")
    logger.warning(f"[警告] task_id={task_id} | 主体名称识别未实现, 跳过")
    return state
