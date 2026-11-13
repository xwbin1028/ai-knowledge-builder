"""
入口识别服务模块。

纯函数服务，负责校验输入文件路径并识别文件类型，
将识别结果回写到图状态中，供后续节点路由使用。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger
from pathlib import Path


def resolve_input_file(state: ImportGraphState) -> ImportGraphState:
    """
    文件类型识别与状态初始化节点。

    核心功能：根据本地文件路径识别文件类型，自动装配对应状态字段，为后续流程路由提供依据。

    业务逻辑：
        1. 校验文件路径是否为空且真实存在。
        2. 根据后缀识别 MD 或 PDF 文件。
        3. 自动填充对应路径、路由开关、文件标题。
        4. 不支持的文件类型直接跳过状态装配。

    Args:
        state (ImportGraphState): 导入流程全局状态，必须包含 local_file_path 和 task_id 字段。

    Returns:
        ImportGraphState: 补全文件信息后的完整状态对象。

    Raises:
        ValueError: 当文件路径为空时抛出。
        FileNotFoundError: 当指定的文件在磁盘上不存在时抛出。
    """
    local_file_path: str = state.get("local_file_path", "")
    task_id: str = state.get("task_id", "")

    # 1. 校验路径是否为空
    if not local_file_path:
        logger.error(
            "文件路径为空，无法识别文件类型 - task_id: {task_id}",
            task_id=task_id
        )
        raise ValueError("文件路径 local_file_path 不能为空")

    file_path = Path(local_file_path)

    # 2. 校验文件是否真实存在 - 补全原注释中的业务意图
    if not file_path.exists():
        logger.error(
            "文件不存在，请检查路径 - task_id: {task_id}, file: {file_path}",
            task_id=task_id,
            file_path=local_file_path
        )
        raise FileNotFoundError(f"文件不存在: {local_file_path}")

    file_suffix = file_path.suffix.lower()
    file_title = file_path.stem

    # 3. 根据文件后缀分流并装配状态
    if file_suffix == ".md":
        logger.info(
            "识别到 Markdown 文件，准备进入图片处理流程 - task_id: {task_id}, file: {file_title}",
            task_id=task_id,
            file_title=file_title
        )
        state["is_md_read_enabled"] = True
        state["is_pdf_read_enabled"] = False
        state["md_path"] = local_file_path
    elif file_suffix == ".pdf":
        logger.info(
            "识别到 PDF 文件，准备进入解析转换流程 - task_id: {task_id}, file: {file_title}",
            task_id=task_id,
            file_title=file_title
        )
        state["is_md_read_enabled"] = False
        state["is_pdf_read_enabled"] = True
        state["pdf_path"] = local_file_path
    else:
        # 不支持的类型直接返回，后续路由会识别到两个开关均为 False 而走向 END
        logger.warning(
            "不支持的文件类型，跳过状态装配 - task_id: {task_id}, file: {file_title}, suffix: {suffix}",
            task_id=task_id,
            file_title=file_title,
            suffix=file_suffix
        )
        return state

    # 回写文件标题
    state["file_title"] = file_title

    return state
