"""
文档切分服务模块。

纯函数服务，按标题层级与语义边界将长文档切分为适合检索的文本块，
构造 chunk 列表并回写到图状态中。
"""
from app.process.import_.agent.state import ImportGraphState


def split_document(state: ImportGraphState) -> ImportGraphState:
    """
    文档切分服务。

    执行步骤：
        1. 按标题层级做一级粗切。
        2. 对超长文本做二次细切。
        3. 构造 chunks 列表。
        4. 回写 chunks。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state
