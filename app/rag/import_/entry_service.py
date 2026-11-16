"""
入口识别服务模块。

纯函数服务，负责校验输入文件路径并识别文件类型，
将识别结果回写到图状态中，供后续节点路由使用。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log
from app.constants.file_constants import ALLOWED_INPUT_SUFFIXES, MD_SUFFIX, PDF_SUFFIX
from pathlib import Path
from typing import Any


@function_log(
    func_name="校验输入文件并识别类型",
    return_names=["state"]
)
def resolve_input_file(state: ImportGraphState) -> ImportGraphState:
    """
    核心功能：校验输入文件并识别类型

    业务逻辑：
        1. 从(state)中获取输入文件的路径(local_file_path)
        2. 判断(local_file_path)
        3. 类型转换(local_file_path: str->local_file_path_po: Path)
        4. 判断(local_file_path_po)
        5. 判断后缀(local_file_path_po_suffix)
        6. 更新(local_file_path_po_suffix)
        7. 返回(state)

    Args:
        (state)流程全局状态

    Returns:
        (state)流程全局状态

    Raises:
        ValueError: 当 local_file_path 缺失、不是字符串或为空白字符串时抛出；
                    当 local_file_path 后缀不在 ALLOWED_INPUT_SUFFIXES 白名单内时抛出；
                    当后缀校验通过但分流分支未命中时抛出。
        FileNotFoundError: 当 local_file_path 指向的路径不存在时抛出；
                           当 local_file_path 指向的路径存在但不是常规文件时抛出。
    """
    # 1. 从(state)中获取输入文件的路径(local_file_path)
    task_id: str = state.get("task_id", "") or ""
    local_file_path: Any = state.get("local_file_path")

    # 2. 判断(local_file_path)
    if not isinstance(local_file_path, str) or not local_file_path.strip():
        logger.error(f"task_id({task_id})【业务终止】-|-输入文件路径非法 local_file_path({local_file_path})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-输入文件路径非法 local_file_path({local_file_path})")

    # 3. 类型转换(local_file_path: str->local_file_path_po: Path)
    local_file_path_po: Path = Path(local_file_path)

    # 4. 判断(local_file_path_po)
    if not local_file_path_po.exists():
        logger.error(f"task_id({task_id})【业务终止】-|-文件不存在 local_file_path_po({local_file_path_po})")
        raise FileNotFoundError(f"task_id({task_id})【业务终止】-|-文件不存在 local_file_path_po({local_file_path_po})")

    if not local_file_path_po.is_file():
        logger.error(f"task_id({task_id})【业务终止】-|-路径不是常规文件 local_file_path_po({local_file_path_po})")
        raise FileNotFoundError(
            f"task_id({task_id})【业务终止】-|-路径不是常规文件 local_file_path_po({local_file_path_po})")

    # 5. 判断后缀(local_file_path_po_suffix)
    local_file_path_po_suffix: str = local_file_path_po.suffix.lower()
    if local_file_path_po_suffix not in ALLOWED_INPUT_SUFFIXES:
        logger.error(
            f"task_id({task_id})【业务终止】-|-文件类型不支持 local_file_path_po_suffix({local_file_path_po_suffix}),仅支持({ALLOWED_INPUT_SUFFIXES})")
        raise ValueError(
            f"task_id({task_id})【业务终止】-|-文件类型不支持 local_file_path_po_suffix({local_file_path_po_suffix}),仅支持({ALLOWED_INPUT_SUFFIXES})")

    # 6. 更新(local_file_path_po_suffix)
    if local_file_path_po_suffix == MD_SUFFIX:
        state["is_md_read_enabled"] = True
        state["is_pdf_read_enabled"] = False
        state["md_path"] = local_file_path
    elif local_file_path_po_suffix == PDF_SUFFIX:
        state["is_md_read_enabled"] = False
        state["is_pdf_read_enabled"] = True
        state["pdf_path"] = local_file_path
    else:
        logger.error(f"task_id({task_id})【业务终止】-|-后缀校验通过但分流未命中 local_file_path_po_suffix({local_file_path_po_suffix})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-后缀校验通过但分流未命中 local_file_path_po_suffix({local_file_path_po_suffix})")

    file_title: str = local_file_path_po.stem
    state["file_title"] = file_title

    # 7. 返回 state
    return state
