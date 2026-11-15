"""
PDF 解析服务模块。

纯函数服务，调用 MinerU 文档解析服务，下载并解压解析结果，
提取 Markdown 路径与正文内容回写到图状态。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log, PROJECT_ROOT
from pathlib import Path


def parse_pdf_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 解析服务主入口。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state


@function_log(
    func_name="输入文件类型识别",
    return_names=["state"],
)
def validates_pdf_paths(state: ImportGraphState) -> tuple[Path, Path]:
    """
    核心功能：输入文件类型识别

    业务逻辑：
        1. 从 state 中获取 local_file_dir(输出文件夹的路径) pdf_path(pdf 文件存储路径)
        2. 判空 pdf_path
        3. 判空 local_file_dir
        4. 转换 Path 对象 pdf_path->pdf_path_po  local_file_dir->local_file_dir_po
        5. 判空 pdf_path_po
        6. 判空 local_file_dir_po
        7. 返回 pdf_path_po  local_file_dir_po

    Args:
        state (ImportGraphState): 流程全局状态。

    Returns:
        tuple[Path, Path]: 返回 pdf 文件路径和输出目录路径。

    Raises:
        ValueError: 当 state 中的 pdf_path 为空时抛出。
        FileNotFoundError: 当 pdf_path_po 指向的路径不存在或不是文件时抛出。
    """
    # 1. 从 state 中获取 local_file_dir pdf_path
    task_id: str = state.get("task_id", "")
    local_file_dir: str = state.get("local_file_dir", "")
    pdf_path: str = state.get("pdf_path", "")

    # 2. 判空 pdf_path
    if not pdf_path:
        logger.error(f"task_id({task_id})【业务终止】-|-文件存储路径为空 pdf_path({pdf_path})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-文件存储路径为空 pdf_path({pdf_path})")

    # 3. 判空 local_file_dir
    if not local_file_dir:
        local_file_dir = PROJECT_ROOT / "output"
        logger.warning(f"task_id({task_id})【业务警告】-|-输出文件夹的路径为空,配置默认值 local_file_dir({local_file_dir})")
        state["local_file_dir"] = str(local_file_dir)

    # 4. 转换 Path 对象 pdf_path->pdf_path_po  local_file_dir->local_file_dir_po
    pdf_path_po: Path = Path(pdf_path)
    local_file_dir_po: Path = Path(local_file_dir)

    # 5. 判空 pdf_path_po
    if not pdf_path_po.is_file():
        logger.error(f"task_id({task_id})【业务终止】-|-文件存储路径为空 pdf_path_po({pdf_path_po})")
        raise FileNotFoundError(f"task_id({task_id})【业务终止】-|-文件存储路径为空 pdf_path_po({pdf_path_po})")

    # 6. 判空 local_file_dir_po
    if not local_file_dir_po.is_dir():
        logger.warning(f"task_id({task_id})【业务警告】-|-输出文件夹的路径为空,创建默认值文件夹 local_file_dir_po({local_file_dir_po})")
        local_file_dir_po.mkdir(parents=True, exist_ok=True)

    return pdf_path_po, local_file_dir_po
