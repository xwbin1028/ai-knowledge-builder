"""
SSE 流式通信.

按 session_id 维护内存队列, 通过 FastAPI StreamingResponse 推送进度与增量.
"""
import asyncio
import json
import queue
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from fastapi import Request

from app.shared.runtime.logger import logger


class SSEEvent(str, Enum):
    """SSE 事件名, 与前端约定一致."""

    READY = "ready"
    PROGRESS = "progress"
    DELTA = "delta"
    FINAL = "final"
    ERROR = "error"
    CLOSE = "__close__"


# key: session_id, value: 线程安全队列
_session_stream: dict[str, queue.Queue] = {}


# ---------------------------------------------------------------------------
# 队列生命周期
# ---------------------------------------------------------------------------
def get_sse_queue(session_id: str) -> queue.Queue | None:
    """
    获取会话队列.

    Args:
        session_id: 会话 ID.

    Returns:
        queue.Queue | None: 队列不存在时返回 None.
    """
    return _session_stream.get(session_id)


def create_sse_queue(session_id: str) -> queue.Queue:
    """
    创建并注册会话队列.

    Args:
        session_id: 会话 ID.

    Returns:
        queue.Queue: 新队列.
    """
    logger.info(f"[提示] session_id={session_id} | 创建 SSE 队列")
    session_queue: queue.Queue = queue.Queue()
    _session_stream[session_id] = session_queue
    return session_queue


def remove_sse_queue(session_id: str) -> None:
    """
    移除会话队列并释放内存.

    Args:
        session_id: 会话 ID.
    """
    logger.info(f"[提示] session_id={session_id} | 移除 SSE 队列")
    _session_stream.pop(session_id, None)


# ---------------------------------------------------------------------------
# 消息推送
# ---------------------------------------------------------------------------
def _sse_pack(event: str, data: dict[str, Any]) -> str:
    """
    打包为 SSE 报文.

    Args:
        event: 事件名.
        data: 业务数据.

    Returns:
        str: event 与 data 两行加空行.
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def push_to_session(session_id: str, event: str, data: dict[str, Any]) -> None:
    """
    向会话队列推送事件.

    Args:
        session_id: 会话 ID.
        event: 事件名, 参考 SSEEvent.
        data: 事件负载.
    """
    session_queue = get_sse_queue(session_id)
    if session_queue is None:
        logger.warning(f"[警告] session_id={session_id} | 队列不存在, 丢弃事件 | event={event}")
        return
    session_queue.put({"event": event, "data": data})


# ---------------------------------------------------------------------------
# SSE 生成器
# ---------------------------------------------------------------------------
async def sse_generator(session_id: str, request: Request) -> AsyncGenerator[str, None]:
    """
    SSE 生成器, 供 StreamingResponse 使用.

    持续拉取队列事件, 客户端断开或收到关闭信号时清理队列.

    Args:
        session_id: 会话 ID.
        request: FastAPI 请求对象, 用于检测断连.

    Yields:
        str: SSE 报文.
    """
    logger.info(f"[提示] session_id={session_id} | SSE 生成器启动")
    session_queue = get_sse_queue(session_id)
    if session_queue is None:
        logger.warning(f"[警告] session_id={session_id} | 队列不存在, 无法推送")
        return

    loop = asyncio.get_running_loop()
    try:
        # 连接建立先发 ready
        yield _sse_pack(SSEEvent.READY.value, {})

        while True:
            # 客户端断开则尽快退出
            if await request.is_disconnected():
                logger.info(f"[提示] session_id={session_id} | 客户端断开")
                break

            try:
                # 阻塞取队列放到线程池, 避免卡住事件循环
                msg = await loop.run_in_executor(None, session_queue.get, True, 1.0)
            except queue.Empty:
                continue

            event = msg.get("event")
            data = msg.get("data")

            if event == SSEEvent.CLOSE.value:
                logger.info(f"[提示] session_id={session_id} | 收到关闭信号")
                break

            yield _sse_pack(event, data)
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        logger.info(f"[提示] session_id={session_id} | 连接取消或对端断开")
        return
    except Exception:
        logger.exception(f"[异常] session_id={session_id} | SSE 推送异常")
    finally:
        logger.info(f"[提示] session_id={session_id} | SSE 生成器结束")
        remove_sse_queue(session_id)
