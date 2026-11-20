"""
节点: Markdown 图片增强.

读取 state 的 md_path, 为图片生成说明并替换地址, 回写 md_content 与 md_path.
"""
from app.constants.node_constants import NODE_MD_IMG
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.enrich_markdown_images import enrich_markdown_images
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_MD_IMG)
def node_md_img(state: ImportGraphState) -> ImportGraphState:
    """
    节点: Markdown 图片增强.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 图片地址已替换的状态.
    """
    add_running_task(state["task_id"], NODE_MD_IMG)
    state = enrich_markdown_images(state)
    add_done_task(state["task_id"], NODE_MD_IMG)
    return state


if __name__ == "__main__":
    from app.shared.runtime.logger import PROJECT_ROOT
    from app.shared.runtime.logger import logger
    import os

    logger.info(f"本地测试 - 项目根目录：{PROJECT_ROOT}")

    test_md_name = os.path.join(r"output\hak180使用说明书", "hak180使用说明书.md")
    test_md_path = os.path.join(PROJECT_ROOT, test_md_name)

    if not os.path.exists(test_md_path):
        logger.error(f"本地测试 - 测试文件不存在：{test_md_path}")
        logger.info("请检查文件路径，或手动将测试MD文件放入项目根目录的output目录下")
    else:
        test_state = {
            "md_path": test_md_path,
            "task_id": "test_task_123456",
            "md_content": "",
        }
        logger.info("开始本地测试 - MD图片处理全流程")
        result_state = node_md_img(test_state)
        logger.info(f"本地测试完成 - 处理结果状态：{result_state}")