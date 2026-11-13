"""
主体名称识别服务模块。

纯函数服务，基于文档切片构造上下文并调用 LLM 识别核心实体名称，
将识别结果回填到状态与切片数据中，并同步写入主题名称索引。
"""
from app.process.import_.agent.state import ImportGraphState


def recognize_and_index_item_name(state: ImportGraphState) -> ImportGraphState:
    """
    主体识别服务。

    执行步骤：
        1. 基于 chunks 构造上下文。
        2. 调用 LLM 识别 item_name。
        3. 将 item_name 回填到 state 和 chunks。
        4. 同步写入主题名称索引。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state
