"""
业务异常工具.

统一失败处理: 先记 [终止] 日志, 再抛出同文案异常, 避免日志与异常文案两处维护.
"""
from typing import Any

from app.shared.runtime.logger import logger


def business_error(
    exc_type: type[Exception],
    task_id: str,
    reason: str,
    **fields: Any,
) -> Exception:
    """
    记录终止日志并构造同文案异常.

    Args:
        exc_type: 异常类型, 如 ValueError.
        task_id: 任务 ID, 为空时省略.
        reason: 失败原因, 一句话.
        **fields: 排错字段, 建议 1-3 个, 如 md_path=...

    Returns:
        Exception: 调用方直接 raise 的异常实例.
    """
    parts: list[str] = []
    if task_id:
        parts.append(f"task_id={task_id}")
    parts.append(reason)
    parts.extend(f"{name}={value}" for name, value in fields.items())
    message = " | ".join(parts)
    logger.error(f"[终止] {message}")
    return exc_type(message)
