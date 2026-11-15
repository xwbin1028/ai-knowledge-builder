"""
项目日志工具模块。

基于 loguru 提供统一日志能力：通过 .env 控制控制台与文件双输出，
文件日志默认写入 ``logs/app_YYYYMMDD.log``。

主要特性：
    1. 配置驱动：通过 .env 开关输出目标，并调整日志级别。
    2. 自动路径：文件日志默认输出到“项目根目录/logs/app_YYYYMMDD.log”。
    3. 自动清理：按配置保留日志，并自动删除过期文件。
    4. 中文友好：使用 UTF-8 编码，避免中文乱码。
    5. 异步安全：启用异步入队，适配多线程/异步场景，减少日志错乱。
    6. 开箱即用：业务模块直接导入 logger 即可使用。
    7. 调用位置精准：过滤 loguru 内部帧与本模块自身帧，定位业务代码实际调用位置。
"""
# ---------------------------------------------------------------------------
# 依赖导入
# ---------------------------------------------------------------------------
import sys
import inspect
import os
import time
from pathlib import Path
from functools import wraps
from typing import Any, Callable, Mapping
from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# 环境配置加载
# ---------------------------------------------------------------------------
# 加载 .env 配置文件默认不覆盖已存在的环境变量
load_dotenv()

# 读取 .env 配置项；缺失时回退到默认值，避免配置缺失导致启动失败
LOG_CONSOLE_ENABLE = os.getenv("LOG_CONSOLE_ENABLE", "True").lower() == "true"
LOG_CONSOLE_LEVEL = os.getenv("LOG_CONSOLE_LEVEL", "INFO").upper()
LOG_FILE_ENABLE = os.getenv("LOG_FILE_ENABLE", "True").lower() == "true"
LOG_FILE_LEVEL = os.getenv("LOG_FILE_LEVEL", "INFO").upper()
LOG_FILE_RETENTION = os.getenv("LOG_FILE_RETENTION", "30 days")

# ---------------------------------------------------------------------------
# 路径与格式常量
# ---------------------------------------------------------------------------
# 日志路径：基于当前文件位置向上推导项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE_NAME = "app_{time:YYYYMMDD}.log"
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME

# 日志格式：包含时间、级别、模块名、函数名、行号和消息，便于阅读与定位
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
    初始化并返回全局日志配置。

    装配步骤：
        1. 移除 loguru 默认控制台 handler，避免重复输出。
        2. 按 LOG_CONSOLE_ENABLE 决定是否挂载 stdout handler。
        3. 按 LOG_FILE_ENABLE 决定是否创建 logs 目录并挂载文件 handler。
        4. 为各 handler 统一应用格式、级别、轮转与保留策略。

    Returns:
        loguru.Logger: 完成装配的 logger 实例。
    """
    # 1. 移除 loguru 默认控制台输出，避免重复打印
    logger.remove()

    # 2. 若 .env 启用控制台输出，则添加 stdout sink
    if LOG_CONSOLE_ENABLE:
        logger.add(
            sink=sys.stdout,
            level=LOG_CONSOLE_LEVEL,
            format=LOG_FORMAT,
            colorize=True,
            enqueue=True
        )

    # 3. 若 .env 启用文件输出，则创建日志目录并添加文件 sink
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
            diagnose=True
        )

    return logger


# 初始化基础 logger，供后续统一修正调用位置
base_logger = init_logger()


# ---------------------------------------------------------------------------
# 调用位置修正
# ---------------------------------------------------------------------------
def fix_log_position(record):
    """
    修正日志记录中的调用位置字段。

    loguru 默认记录的 name/function/line 指向框架内部帧。本函数遍历调用栈，
    跳过 loguru 内部帧与本模块自身帧，将 record 中的位置字段改写为业务代码
    的实际调用点。

    Args:
        record (dict): loguru 传给 patcher 的日志记录字典，原地修改。
    """
    for frame in inspect.stack():
        # 过滤 loguru 内部帧和本工具模块 logger.py 自身帧，定位业务代码调用位置
        if ("_logger.py" in frame.filename or frame.function == "_log") or "logger.py" in frame.filename:
            continue
        # 更新日志字段为业务代码实际位置
        record.update(
            name=frame.filename.split("/")[-1].split("\\")[-1],
            function=frame.function,
            line=frame.lineno
        )
        break


# 为 logger 打补丁，使每条日志记录都修正为业务代码实际调用位置
logger = base_logger.patch(fix_log_position)


# ---------------------------------------------------------------------------
# 装饰器工具
# ---------------------------------------------------------------------------
def _trace_id(state) -> str:
    """
    从节点 state 中提取追踪 ID。

    取值优先级为 session_id > task_id；两者均缺失或 state 不是映射类型时，
    返回占位符 "-"，保证日志格式稳定且不因缺字段抛错。

    Args:
        state: 节点上下文，通常为包含 session_id / task_id 的 Mapping。

    Returns:
        str: 追踪 ID，缺失时为 "-"。
    """
    if isinstance(state, Mapping):
        return str(state.get("session_id") or state.get("task_id") or "-")
    return "-"


def node_log(node_name: str):
    """
    节点日志装饰器，适用于首个参数为 state 的图/流水线节点函数。

    自动记录三类事件：
        - 节点开始：节点名 + 追踪 ID。
        - 节点完成：节点名 + 追踪 ID + 耗时毫秒。
        - 节点异常：节点名 + 追踪 ID + 完整堆栈，并原样抛出异常。

    被装饰函数契约：
        - 第一个位置参数必须是 state，用于提取追踪 ID；
        - 返回值原样透传，装饰器不改变业务返回值；
        - 异常不吞没，记录堆栈后重新抛出。

    Args:
        node_name (str): 节点名称，用于日志标识。

    Returns:
        Callable: 装饰器。
    """

    def deco(func):
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            # 解析追踪 ID，用于串联同一次请求下的各节点日志
            trace_id = _trace_id(state)
            start_ts = time.time()
            logger.info(f"[{node_name}] 节点开始，追踪ID={trace_id}")
            try:
                result = func(state, *args, **kwargs)
                # 计算节点耗时毫秒，用于性能观测
                cost_ms = int((time.time() - start_ts) * 1000)
                logger.info(f"[{node_name}] 节点完成，追踪ID={trace_id}，耗时={cost_ms}ms")
                return result
            except Exception:
                # 记录完整堆栈后原样抛出，保持上层异常处理语义
                logger.exception(f"[{node_name}] 节点异常，追踪ID={trace_id}")
                raise

        return wrapper

    return deco


def step_log(step_name: str):
    """
    步骤日志装饰器，适用于任意普通函数。

    自动记录步骤开始、步骤完成及耗时；发生异常时记录完整堆栈后重新抛出，
    不吞异常，保持原有业务语义。

    Args:
        step_name (str): 步骤名称，用于日志标识。

    Returns:
        Callable: 装饰器。
    """

    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_ts = time.time()
            logger.info(f"[{step_name}] 步骤开始")
            try:
                result = func(*args, **kwargs)
                # 计算步骤耗时毫秒，用于性能观测
                cost_ms = int((time.time() - start_ts) * 1000)
                logger.info(f"[{step_name}] 步骤完成，耗时={cost_ms}ms")
                return result
            except Exception:
                # 记录完整堆栈后原样抛出，保持上层异常处理语义
                logger.exception(f"[{step_name}] 步骤异常")
                raise

        return wrapper

    return deco


# ---------------------------------------------------------------------------
# 函数调用日志装饰器
# ---------------------------------------------------------------------------
# 敏感参数关键词：命中即脱敏
_SENSITIVE_KEYWORDS = (
    "password", "passwd", "pwd", "token", "secret", "api_key", "apikey",
    "access_key", "private_key", "authorization", "cookie", "credential",
)
_MAX_VALUE_LEN = 200
_MAX_ITEMS = 10


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return any(k in lowered for k in _SENSITIVE_KEYWORDS)


def _safe_repr(value: Any, max_len: int = _MAX_VALUE_LEN) -> str:
    """安全、可读、截断地表示任意对象，绝不因 __repr__ 抛错而拖垮业务。"""
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
    """把实参按 name=value 整理，覆盖位置参数 / 关键字 / 默认值 / *args / **kwargs。"""
    try:
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
    except (TypeError, ValueError):
        return f"args={_safe_repr(args)}, kwargs={_safe_repr(kwargs)}"

    parts: list[str] = []
    for name, value in bound.arguments.items():
        param = sig.parameters.get(name)
        # 跳过未传入且为空的 *args / **kwargs，避免日志噪音
        if (
            param is not None
            and param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and not value
        ):
            continue
        parts.append(f"{name}=***" if _is_sensitive(name) else f"{name}={_safe_repr(value)}")
    return ", ".join(parts) if parts else "<无参数>"


def _format_return(value: Any, return_names: list[str] | None = None) -> str:
    """把返回值整理为可读文本；无返回值时明确标注。"""
    if value is None:
        return "无返回值"
    if isinstance(value, (tuple, list)):
        if not value:
            return "无返回值（空容器）"
        if return_names and len(return_names) == len(value):
            return ", ".join(f"{n}={_safe_repr(v)}" for n, v in zip(return_names, value))
        if len(value) <= _MAX_ITEMS:
            return ", ".join(f"result[{i}]={_safe_repr(v)}" for i, v in enumerate(value))
        preview = ", ".join(f"result[{i}]={_safe_repr(v)}" for i, v in enumerate(value[:_MAX_ITEMS]))
        return f"{preview}, ... <total={len(value)}>"
    if isinstance(value, dict):
        items = list(value.items())
        if len(items) <= _MAX_ITEMS:
            return ", ".join(f"result[{k!r}]={_safe_repr(v)}" for k, v in items)
        preview = ", ".join(f"result[{k!r}]={_safe_repr(v)}" for k, v in items[:_MAX_ITEMS])
        return f"{preview}, ... <total={len(items)}>"
    return f"result={_safe_repr(value)}"


def _resolve_call_site(target: Callable) -> tuple[str, str, int]:
    """解析被装饰函数自身的 (py 文件名, 函数名, def 行号)，作为日志中的位置字段。"""
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


def function_log(
    func: Callable | None = None,
    *,
    func_name: str | None = None,
    return_names: list[str] | None = None,
):
    """
    通用函数调用日志装饰器，同步/异步函数均适用。

    日志位置（name/function/line）绑定被装饰函数自身，而非 wrapper 或调用方；
    开始记录参数名=参数值，完成记录返回值（无返回值时明确标注），异常记录堆栈
    并原样抛出。支持 @function_log 与 @function_log(...) 两种写法。

    Args:
        func: 被装饰函数，@function_log 裸用时自动传入。
        func_name: 日志业务名，缺省用真实函数名。
        return_names: tuple/list 返回值逐项命名，如 ["pdf_path_obj", "local_dir_obj"]。
    """

    def deco(target: Callable):
        log_name = func_name or target.__name__
        file_name, real_name, def_line = _resolve_call_site(target)

        def position_patcher(record: dict) -> None:
            record.update(name=file_name, function=real_name, line=def_line)

        # 关键：用 base_logger 绕过 fix_log_position 的栈遍历，位置直接绑定被装饰函数
        target_logger = base_logger.patch(position_patcher)

        if inspect.iscoroutinefunction(target):
            @wraps(target)
            async def async_wrapper(*args, **kwargs):
                params_text = _format_params(target, args, kwargs)
                start_ts = time.time()
                target_logger.info(f"[{log_name}] 开始执行 | 参数: {params_text}")
                try:
                    result = await target(*args, **kwargs)
                    cost_ms = int((time.time() - start_ts) * 1000)
                    target_logger.info(
                        f"[{log_name}] 执行完毕 | {_format_return(result, return_names)} | 耗时={cost_ms}ms"
                    )
                    return result
                except Exception:
                    cost_ms = int((time.time() - start_ts) * 1000)
                    target_logger.exception(f"[{log_name}] 执行异常 | 耗时={cost_ms}ms")
                    raise
            return async_wrapper

        @wraps(target)
        def sync_wrapper(*args, **kwargs):
            params_text = _format_params(target, args, kwargs)
            start_ts = time.time()
            target_logger.info(f"[{log_name}] 开始执行 | 参数: {params_text}")
            try:
                result = target(*args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.info(
                    f"[{log_name}] 执行完毕 | {_format_return(result, return_names)} | 耗时={cost_ms}ms"
                )
                return result
            except Exception:
                cost_ms = int((time.time() - start_ts) * 1000)
                target_logger.exception(f"[{log_name}] 执行异常 | 耗时={cost_ms}ms")
                raise

        return sync_wrapper

    if func is not None:
        return deco(func)
    return deco
