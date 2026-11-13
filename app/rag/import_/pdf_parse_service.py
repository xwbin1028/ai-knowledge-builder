"""
PDF 解析服务模块。

纯函数服务，调用 MinerU 文档解析服务，下载并解压解析结果，
提取 Markdown 路径与正文内容回写到图状态。
"""
from app.process.import_.agent.state import ImportGraphState


def parse_pdf_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 解析服务。

    执行步骤：
        1. 调用 MinerU 解析服务。
        2. 下载并解压解析结果。
        3. 获取 Markdown 路径与正文内容。
        4. 回写 md_path / md_content / local_dir。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state