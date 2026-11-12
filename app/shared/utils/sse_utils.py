"""
SSE 流式通信工具模块。

基于 FastAPI StreamingResponse 与内存队列实现 Server-Sent Events。
为每个会话维护独立的阻塞队列，通过线程池适配异步事件循环，
支持进度推送、LLM 增量输出与断连检测。
"""
import json
import queue
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import Request


# ---------------------------------------------------------------------------
# SSE 事件类型常量
# ---------------------------------------------------------------------------
class SSEEvent:
    """
    SSE 支持的事件类型枚举。
    """
    READY = "ready"         # 连接建立
    PROGRESS = "progress"   # 任务节点进度
    DELTA = "delta"         # LLM 流式输出增量
    FINAL = "final"         # 最终完整答案
    ERROR = "error"         # 错误信息
    CLOSE = "__close__"     # 关闭连接信号


# 全局 SSE 会话队列存储
# Key: session_id, Value: queue.Queue
_session_stream: Dict[str, queue.Queue] = {}


# ---------------------------------------------------------------------------
# 队列生命周期管理
# ---------------------------------------------------------------------------
def get_sse_queue(session_id: str) -> Optional["queue.Queue"]:
    """
    获取指定 session 的队列，不存在时返回 None。

    Args:
        session_id (str): 会话唯一标识。

    Returns:
        Optional[queue.Queue]: 对应的队列对象，若不存在则返回 None。
    """
    return _session_stream.get(session_id)


def create_sse_queue(session_id: str) -> "queue.Queue":
    """
    创建并注册一个新的 SSE 队列。

    Args:
        session_id (str): 会话唯一标识。

    Returns:
        queue.Queue: 新创建的线程安全队列实例。
    """
    print(f"[SSE] Creating queue for session: {session_id}")
    q = queue.Queue()
    _session_stream[session_id] = q
    return q


def remove_sse_queue(session_id: str) -> None:
    """
    移除指定 session 的队列，释放内存。

    Args:
        session_id (str): 会话唯一标识。
    """
    print(f"[SSE] Removing queue for session: {session_id}")
    _session_stream.pop(session_id, None)


# ---------------------------------------------------------------------------
# 消息推送
# ---------------------------------------------------------------------------
def _sse_pack(event: str, data: Dict[str, Any]) -> str:
    """
    将事件与数据打包为 SSE 标准报文格式。

    Args:
        event (str): 事件类型名称，如 ready 或 progress。
        data (Dict[str, Any]): 需要推送给前端的业务数据字典。

    Returns:
        str: 符合 SSE 协议规范的多行字符串报文。
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def push_to_session(session_id: str, event: str, data: Dict[str, Any]) -> None:
    """
    通过 session_id 将事件推送到对应的队列。

    Args:
        session_id (str): 会话标识。
        event (str): 事件类型，参考 SSEEvent 常量。
        data (Dict[str, Any]): 事件负载数据。
    """
    stream_queue = get_sse_queue(session_id)
    if stream_queue:
        stream_queue.put({"event": event, "data": data})
    else:
        print(f"[SSE] Warning: No queue found for session {session_id} when pushing {event}")


# ---------------------------------------------------------------------------
# SSE 生成器 (FastAPI StreamingResponse 入口)
# ---------------------------------------------------------------------------
async def sse_generator(session_id: str, request: Request):
    """
    SSE 生成器，用于 FastAPI 的 StreamingResponse。

    持续从会话队列拉取事件并 yield 给客户端，同时轮询客户端连接状态，
    在断连或收到 __close__ 信号时清理资源并退出。

    Args:
        session_id (str): 会话标识。
        request (Request): FastAPI 的请求对象，用于检测客户端断连。

    Yields:
        str: 格式化后的 SSE 报文数据块。
    """
    print(f"[SSE] Generator started for session: {session_id}")
    stream_queue = get_sse_queue(session_id)
    if stream_queue is None:
        print(f"[SSE] Error: Queue not found for session {session_id}. Available sessions: {list(_session_stream.keys())}")
        return

    loop = asyncio.get_running_loop()
    try:
        # 发送连接建立信号
        print(f"[SSE] Sending ready signal for {session_id}")
        yield _sse_pack("ready", {})

        while True:
            # 若客户端断开，尽快退出
            if await request.is_disconnected():
                print(f"[SSE] Client disconnected: {session_id}")
                print("-----------------------断开连接--------------------")
                break

            try:
                # 使用 run_in_executor 避免阻塞 async 事件循环
                # 传入阻塞的 queue.get 及超时时间 1.0 秒
                msg = await loop.run_in_executor(None, stream_queue.get, True, 1.0)
            except queue.Empty:
                continue

            event = msg.get("event")
            data = msg.get("data")

            # 特殊关闭事件
            if event == "__close__":
                print(f"[SSE] Closing signal received for {session_id}")
                break

            yield _sse_pack(event, data)
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        print(f"[SSE] Client disconnected (Cancelled/Reset/Pipe): {session_id}")
        # 生成器被取消/对端断开：静默退出
        return
    except Exception as e:
        print(f"[SSE] Exception in generator for {session_id}: {e}")
    finally:
        print(f"[SSE] Generator finished for {session_id}")
        # 清理资源
        remove_sse_queue(session_id)