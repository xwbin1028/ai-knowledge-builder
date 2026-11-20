"""
统一日志组件.

基于 loguru, 由 .env 控制控制台与文件双输出, 文件写入 logs/app_YYYYMMDD.log.
业务侧只导入 logger; 节点与服务分别用 node_log 与 function_log 打点.
"""
import inspect
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Mapping

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# 环境配置
# ---------------------------------------------------------------------------
# 加载 .env, 不覆盖已存在的系统环境变量
load_dotenv()

# 缺省值兜底, 避免配置缺失导致启动失败
LOG_CONSOLE_ENABLE = os.getenv("LOG_CONSOLE_ENABLE", "True").lower() == "true"
LOG_CONSOLE_LEVEL = os.getenv("LOG_CONSOLE_LEVEL", "INFO").upper()
LOG_FILE_ENABLE = os.getenv("LOG_FILE_ENABLE", "True").lower() == "true"
LOG_FILE_LEVEL = os.getenv("LOG_FILE_LEVEL", "INFO").upper()
LOG_FILE_RETENTION = os.getenv("LOG_FILE_RETENTION", "30 days")

# ---------------------------------------------------------------------------
# 路径与格式
# ---------------------------------------------------------------------------
# 项目根目录, 供其他模块定位资源
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE_NAME = "app_{time:YYYYMMDD}.log"
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME

# 时间 级别 文件 函数 行号 消息
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name: <20}</cyan>:<cyan>{function: <15}</cyan>:<cyan>{line: <4}</cyan> - "
    "<level>{message}</level>"
)


# ---------------------------------------------------------------------------
# 日志装配
# ---------------------------------------------------------------------------
def init_logger():
    """
    装配并返回 logger.

    业务逻辑:
        1. 移除 loguru 默认控制台, 避免重复输出
        2. 按 .env 挂载控制台 sink
        3. 按 .env 挂载文件 sink

    Returns:
        loguru.Logger: 装配后的 logger.
    """
    # 1. 移除默认控制台, 避免重复输出
    logger.remove()

    # 2. 控制台 sink
    if LOG_CONSOLE_ENABLE:
        logger.add(
            sink=sys.stdout,
            level=LOG_CONSOLE_LEVEL,
            format=LOG_FORMAT,
            colorize=True,
            enqueue=True,
        )

    # 3. 文件 sink, 按天轮转并按保留期清理
    if LOG_FILE_ENABLE:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            sink=LOG_FILE_PATH,
            level=LOG_FILE_LEVEL,
            format=LOG_FORMAT,
            rotation="00:00",
            retention=LOG_FILE_RETENTION,
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    return logger


_base_logger = init_logger()


# 本模块绝对路径, 用于过滤自身帧
_SELF_PATH = os.path.normcase(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 调用位置修正
# ---------------------------------------------------------------------------
def _fix_log_position(record: dict) -> None:
    """
    把日志位置改写为业务代码调用点.

    loguru 默认记录框架内部帧, 这里跳过 loguru 与本模块的帧, 原地修改 record.

    Args:
        record: loguru 传给 patcher 的记录字典.
    """
    for frame in inspect.stack():
        filename = frame.filename
        # 过滤 loguru 内部帧, 本模块帧与统一异常工具的帧
        if (
            os.path.normcase(os.path.abspath(filename)) == _SELF_PATH
            or os.path.basename(filename) in ("_logger.py", "error_utils.py")
            or frame.function == "_log"
        ):
            continue
        record.update(
            name=os.path.basename(filename),
            function=frame.function,
            line=frame.lineno,
        )
        break


# 每条日志都修正到业务调用位置
logger = _base_logger.patch(_fix_log_position)


# ---------------------------------------------------------------------------
# 节点与步骤装饰器
# ---------------------------------------------------------------------------
def _trace_id(state) -> str:
    """
    从 state 提取追踪 ID.

    优先级 session_id > task_id, 都缺失时返回 "-".

    Args:
        state: 节点上下文, 通常是 Mapping.

    Returns:
        str: 追踪 ID.
    """
    if isinstance(state, Mapping):
        return str(state.get("session_id") or state.get("task_id") or "-")
    return "-"


def _resolve_call_site(target: Callable) -> tuple[str, str, int]:
    """解析被装饰函数的 文件名 函数名 def 行号, 作为日志位置字段."""
    try:
        source_file = inspect.getsourcefile(target)
        file_name = Path(source_file).name if source_file else "<unknown>"
    except (TypeError, OSError):
        file_name = "<unknown>"
    try:
        lines, start = inspect.getsourcelines(target)
        for offset, line in enumerate(lines):
            if line.lstrip().startswith(("def ", "async def ")):
                return file_name, target.__name__, start + offset
        return file_name, target.__name__, start
    except (TypeError, OSError):
        return file_name, target.__name__, target.__code__.co_firstlineno


def node_log(node_name: str):
    """
    节点日志装饰器, 适用于首参为 state 的图节点.

    记录开始 完成 耗时 与异常堆栈, 不改业务返回值.

    Args:
        node_name: 节点名, 来自 node_constants.

    Returns:
        Callable: 装饰器.
    """

    def deco(func):
        # 位置绑定被装饰节点, 而不是 wrapper 或 langgraph 调用方
        file_name, real_name, def_line = _resolve_call_site(func)

        def position_patcher(record: dict) -> None:
            record.update(name=file_name, function=real_name, line=def_line)

        target_logger = _base_logger.patch(position_patcher)

        @wraps(func)
        def wrapper(state, *args, **kwargs):
            trace_id = _trace_id(state)
            start_ts = time.time()
            target_logger.info(f"[节点] {node_name} 开始 | task_id={trace_id}")
            try:
                result = func(state, *args, **kwargs)
            except Exception:
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.exception(
                    f"[节点] {node_name} 异常 | task_id={trace_id} | 耗时={cost_ms}ms"
                )
                raise
            cost_ms = int((time.time() - start_ts) * 1000)
            target_logger.info(f"[节点] {node_name} 完成 | task_id={trace_id} | 耗时={cost_ms}ms")
            return result

        return wrapper

    return deco


def step_log(step_name: str):
    """
    步骤日志装饰器, 适用于任意普通函数.

    Args:
        step_name: 步骤名, 用于日志标识.

    Returns:
        Callable: 装饰器.
    """

    def deco(func):
        # 位置绑定被装饰函数, 而不是 wrapper 或调用方
        file_name, real_name, def_line = _resolve_call_site(func)

        def position_patcher(record: dict) -> None:
            record.update(name=file_name, function=real_name, line=def_line)

        target_logger = _base_logger.patch(position_patcher)

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_ts = time.time()
            target_logger.info(f"[步骤] {step_name} 开始")
            try:
                result = func(*args, **kwargs)
            except Exception:
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.exception(f"[步骤] {step_name} 异常 | 耗时={cost_ms}ms")
                raise
            cost_ms = int((time.time() - start_ts) * 1000)
            target_logger.info(f"[步骤] {step_name} 完成 | 耗时={cost_ms}ms")
            return result

        return wrapper

    return deco


# ---------------------------------------------------------------------------
# 函数调用日志装饰器
# ---------------------------------------------------------------------------
# 命中即脱敏的参数关键字
_SENSITIVE_KEYWORDS = (
    "password", "passwd", "pwd", "token", "secret", "api_key", "apikey",
    "access_key", "private_key", "authorization", "cookie", "credential",
)
_MAX_VALUE_LEN = 200
_MAX_ITEMS = 10


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS)


def _safe_repr(value: Any, max_len: int = _MAX_VALUE_LEN) -> str:
    """安全 可读 截断地表示对象, 不因 __repr__ 抛错拖垮业务."""
    try:
        if isinstance(value, str):
            return value if len(value) <= max_len else f"{value[:max_len]}...<len={len(value)}>"
        if isinstance(value, (list, tuple, set, frozenset)):
            items = list(value)
            if len(items) <= _MAX_ITEMS:
                return repr(value)
            preview = ", ".join(_safe_repr(v, max_len // 2) for v in items[:_MAX_ITEMS])
            return f"[{preview}, ... <total={len(items)}>]"
        if isinstance(value, dict):
            if len(value) <= _MAX_ITEMS:
                return repr(value)
            preview = ", ".join(
                f"{k!r}: {_safe_repr(v, max_len // 2)}"
                for k, v in list(value.items())[:_MAX_ITEMS]
            )
            return f"{{{preview}, ... <total={len(value)}>}}"
        text = repr(value)
        return text if len(text) <= max_len else f"{text[:max_len]}...<truncated>"
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"


def _format_params(func: Callable, args: tuple, kwargs: dict) -> str:
    """按 name=value 整理实参, 覆盖位置 关键字 默认值与可变参数."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
    except (TypeError, ValueError):
        return f"args={_safe_repr(args)}, kwargs={_safe_repr(kwargs)}"

    parts: list[str] = []
    for name, value in bound.arguments.items():
        param = sig.parameters.get(name)
        # *args 与 **kwargs 为空时不打印, 减少噪音
        if (
            param is not None
            and param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and not value
        ):
            continue
        parts.append(f"{name}=***" if _is_sensitive(name) else f"{name}={_safe_repr(value)}")
    return ", ".join(parts) if parts else "<无参数>"


def _format_return(value: Any, return_names: list[str] | None = None) -> str:
    """把返回值整理为可读文本, 无返回值时明确标注."""
    if value is None:
        return "无返回值"
    if isinstance(value, (tuple, list)):
        if not value:
            return "无返回值, 空容器"
        if return_names and len(return_names) == len(value):
            return ", ".join(f"{name}={_safe_repr(v)}" for name, v in zip(return_names, value))
        if len(value) <= _MAX_ITEMS:
            return ", ".join(f"result[{i}]={_safe_repr(v)}" for i, v in enumerate(value))
        preview = ", ".join(
            f"result[{i}]={_safe_repr(v)}" for i, v in enumerate(value[:_MAX_ITEMS])
        )
        return f"{preview}, ... <total={len(value)}>"
    if isinstance(value, dict):
        items = list(value.items())
        if len(items) <= _MAX_ITEMS:
            return ", ".join(f"result[{k!r}]={_safe_repr(v)}" for k, v in items)
        preview = ", ".join(f"result[{k!r}]={_safe_repr(v)}" for k, v in items[:_MAX_ITEMS])
        return f"{preview}, ... <total={len(items)}>"
    return f"result={_safe_repr(value)}"


def function_log(
    func: Callable | None = None,
    *,
    func_name: str | None = None,
    return_names: list[str] | None = None,
):
    """
    函数调用日志装饰器, 同步与异步函数均适用.

    开始记参数, 完成记返回值与耗时, 异常记堆栈并原样抛出.
    日志位置绑定被装饰函数, 而不是 wrapper 或调用方.
    支持 @function_log 与 @function_log(...) 两种写法.

    Args:
        func: 被装饰函数, 裸用时自动传入.
        func_name: 日志业务名, 缺省用真实函数名.
        return_names: 多返回值逐项命名, 如 ["md_path", "md_content"].

    Returns:
        Callable: 装饰后的函数, 或装饰器.
    """

    def deco(target: Callable):
        log_name = func_name or target.__name__
        file_name, real_name, def_line = _resolve_call_site(target)

        def position_patcher(record: dict) -> None:
            record.update(name=file_name, function=real_name, line=def_line)

        # 用 _base_logger 绕过栈遍历, 位置直接绑定被装饰函数
        target_logger = _base_logger.patch(position_patcher)

        if inspect.iscoroutinefunction(target):
            @wraps(target)
            async def async_wrapper(*args, **kwargs):
                params_text = _format_params(target, args, kwargs)
                start_ts = time.time()
                target_logger.info(f"[提示] {log_name} 开始 | {params_text}")
                try:
                    result = await target(*args, **kwargs)
                except Exception:
                    cost_ms = int((time.time() - start_ts) * 1000)
                    target_logger.exception(f"[异常] {log_name} 异常 | 耗时={cost_ms}ms")
                    raise
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.info(
                    f"[提示] {log_name} 完成 | {_format_return(result, return_names)} | 耗时={cost_ms}ms"
                )
                return result

            return async_wrapper

        @wraps(target)
        def sync_wrapper(*args, **kwargs):
            params_text = _format_params(target, args, kwargs)
            start_ts = time.time()
            target_logger.info(f"[提示] {log_name} 开始 | {params_text}")
            try:
                result = target(*args, **kwargs)
            except Exception:
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.exception(f"[异常] {log_name} 异常 | 耗时={cost_ms}ms")
                raise
            cost_ms = int((time.time() - start_ts) * 1000)
            target_logger.info(
                f"[提示] {log_name} 完成 | {_format_return(result, return_names)} | 耗时={cost_ms}ms"
            )
            return result

        return sync_wrapper

    if func is not None:
        return deco(func)
    return deco
