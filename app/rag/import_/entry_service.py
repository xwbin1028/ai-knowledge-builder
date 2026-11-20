"""
入口文件校验与类型识别.

校验 local_file_path, 识别 md 或 pdf, 回写分支标志与 file_title.
"""
from pathlib import Path
from typing import Any

from app.constants.file_constants import ALLOWED_INPUT_SUFFIXES, MD_SUFFIX, PDF_SUFFIX
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import function_log


@function_log(func_name="校验输入文件并识别类型", return_names=["state"])
def resolve_input_file(state: ImportGraphState) -> ImportGraphState:
    """
    校验输入文件并识别类型.

    业务逻辑:
        1. 从 state 取 task_id 与 local_file_path
        2. 校验 local_file_path 为非空字符串
        3. 转 Path 并校验文件存在
        4. 校验后缀在白名单内
        5. 按后缀写分支标志
        6. 回写 file_title

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入类型标志的状态.

    Raises:
        ValueError: 路径非法或后缀不支持.
        FileNotFoundError: 文件不存在或不是常规文件.
    """
    # 1. 从 state 取 task_id 与 local_file_path
    task_id: str = state.get("task_id", "")
    local_file_path: Any = state.get("local_file_path")

    # 2. 校验 local_file_path 为非空字符串
    if not isinstance(local_file_path, str) or not local_file_path.strip():
        raise business_error(ValueError, task_id, "输入文件路径非法", local_file_path=local_file_path)

    # 3. 转 Path 并校验文件存在
    local_file_path_po: Path = Path(local_file_path)
    if not local_file_path_po.exists():
        raise business_error(FileNotFoundError, task_id, "输入文件不存在", path=local_file_path_po)
    if not local_file_path_po.is_file():
        raise business_error(FileNotFoundError, task_id, "输入路径不是常规文件", path=local_file_path_po)

    # 4. 校验后缀在白名单内
    suffix: str = local_file_path_po.suffix.lower()
    if suffix not in ALLOWED_INPUT_SUFFIXES:
        raise business_error(
            ValueError, task_id, "文件类型不支持", suffix=suffix, allowed=ALLOWED_INPUT_SUFFIXES
        )

    # 5. 按后缀写分支标志
    if suffix == MD_SUFFIX:
        state["is_md_read_enabled"] = True
        state["is_pdf_read_enabled"] = False
        state["md_path"] = local_file_path
    elif suffix == PDF_SUFFIX:
        state["is_md_read_enabled"] = False
        state["is_pdf_read_enabled"] = True
        state["pdf_path"] = local_file_path
    else:
        raise business_error(ValueError, task_id, "后缀校验通过但分流未命中", suffix=suffix)

    # 6. 回写 file_title
    state["file_title"] = local_file_path_po.stem
    return state
