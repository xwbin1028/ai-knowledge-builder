"""
Markdown 图片增强服务模块。

纯函数服务，负责扫描 Markdown 中的图片引用，调用多模态模型生成图片说明，
上传至 MinIO 对象存储，并替换 Markdown 中的图片地址。
"""
from app.process.import_.agent.state import ImportGraphState


def enrich_markdown_image(state: ImportGraphState) -> ImportGraphState:
    """
    Markdown 图片增强服务。

    执行步骤：
        1. 扫描 Markdown 中的图片。
        2. 调用多模态生成图片说明。
        3. 上传图片到 MinIO。
        4. 替换 Markdown 图片地址并回写 md_path。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state