"""
入口识别服务模块。

纯函数服务，负责校验输入文件路径并识别文件类型，
将识别结果回写到图状态中，供后续节点路由使用。
"""
from app.process.import_.agent.state import ImportGraphState


def resolve_input_file(state: ImportGraphState) -> ImportGraphState:
    """入口识别服务。

    执行步骤：
        1. 校验 local_file_path。
        2. 识别文件类型 PDF 或 Markdown。
        3. 回写 is_pdf_read_enabled / is_md_read_enabled。
        4. 回写 pdf_path / md_path / file_title。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state