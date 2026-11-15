"""
PDF 解析服务模块。

纯函数服务，调用 MinerU 文档解析服务，下载并解压解析结果，
提取 Markdown 路径与正文内容回写到图状态。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log, PROJECT_ROOT
from app.constants.file_constants import DEFAULT_OUTPUT_DIR_NAME
from pathlib import Path
from typing import Any


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
    func_name="校验 PDF 文件路径与输出目录，并返回 Path 对象",
    return_names=["pdf_path_po", "local_file_dir_po"],
)
def validates_pdf_paths(state: ImportGraphState) -> tuple[Path, Path]:
    """
    核心功能：校验 PDF 文件路径与输出目录，并返回 Path 对象

    业务逻辑：
        1. 从(state)中获取输出文件夹的路径(local_file_dir) pdf文件存储路径(pdf_path)
        2. 判断(pdf_path)
        3. 判断(local_file_dir)
        4. 类型转换(pdf_path: str->pdf_path_po:Path)(local_file_dir: str->local_file_dir_po:Path)
        5. 判断(pdf_path_po)
        6. 判断(local_file_dir_po)
        7. 返回(pdf_path_po, local_file_dir_po)

    Args:
        state (ImportGraphState): 流程全局状态。

    Returns:
        tuple[Path, Path]: 返回有效的 PDF 文件 Path 对象和输出目录 Path 对象

    Raises:
        ValueError: 当 state 中的 pdf_path 缺失、不是字符串或为空白字符串时抛出。
        FileNotFoundError: 当 pdf_path 指向的路径不存在，或指向的不是常规文件时抛出。
    """
    # 1. 从(state)中获取输出文件夹的路径(local_file_dir) pdf 文件存储路径(pdf_path)
    task_id: str = state.get("task_id", "") or ""
    local_file_dir: Any = state.get("local_file_dir")
    pdf_path: Any = state.get("pdf_path")

    # 2. 判断(pdf_path)
    if not isinstance(pdf_path, str) or not pdf_path.strip():
        logger.error(f"task_id({task_id})【业务终止】-|-PDF文件存储路径非法 pdf_path({pdf_path})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-PDF文件存储路径非法 pdf_path({pdf_path})")

    # 3. 判断(local_file_dir)
    if not isinstance(local_file_dir, str) or not local_file_dir.strip():
        local_file_dir = str(PROJECT_ROOT / DEFAULT_OUTPUT_DIR_NAME)
        logger.warning(f"task_id({task_id})【业务警告】-|-输出文件夹的路径为空或非法,已配置默认值 local_file_dir({local_file_dir})")
        state["local_file_dir"] = local_file_dir

    # 4. 类型转换(pdf_path: str->pdf_path_po:Path)(local_file_dir: str->local_file_dir_po:Path)
    pdf_path_po: Path = Path(pdf_path)
    local_file_dir_po: Path = Path(local_file_dir)

    # 5. 判断(pdf_path_po)
    if not pdf_path_po.is_file():
        logger.error(f"task_id({task_id})【业务终止】-|-PDF文件不存在或不是常规文件 pdf_path_po({pdf_path_po})")
        raise FileNotFoundError(
            f"task_id({task_id})【业务终止】-|-PDF文件不存在或不是常规文件 pdf_path_po({pdf_path_po})")

    # 6. 判断(local_file_dir_po)
    if not local_file_dir_po.is_dir():
        logger.warning(f"task_id({task_id})【业务警告】-|-输出目录不存在,自动创建 local_file_dir_po({local_file_dir_po})")
        local_file_dir_po.mkdir(parents=True, exist_ok=True)

    # 7. 返回(pdf_path_po, local_file_dir_po)
    return pdf_path_po, local_file_dir_po
