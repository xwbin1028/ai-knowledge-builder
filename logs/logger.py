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

使用示例：
    在业务模块中直接导入即可：
    
    from logger import logger, node_log, step_log
    
    logger.info("业务日志")
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
from typing import Mapping
from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# 环境配置加载
# ---------------------------------------------------------------------------
# 加载 .env 配置文件 (默认不覆盖已存在的环境变量)
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
    """初始化并返回全局日志配置。

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
    """修正日志记录中的调用位置字段。

    loguru 默认记录的 name/function/line 指向框架内部帧。本函数遍历调用栈，
    跳过 loguru 内部帧与本模块自身帧，将 record 中的位置字段改写为业务代码
    的实际调用点。

    Args:
        record (dict): loguru 传给 patcher 的日志记录字典，原地修改。
    """
    for frame in inspect.stack():
        # 过滤 loguru 内部帧和本工具模块 (logger.py)自身帧，定位业务代码调用位置
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
    """从节点 state 中提取追踪 ID。

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
    """节点日志装饰器，适用于首个参数为 state 的图/流水线节点函数。

    自动记录三类事件：
        - 节点开始：节点名 + 追踪 ID。
        - 节点完成：节点名 + 追踪 ID + 耗时 (毫秒)。
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
                # 计算节点耗时 (毫秒)，用于性能观测
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
    """步骤日志装饰器，适用于任意普通函数。

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
                # 计算步骤耗时 (毫秒)，用于性能观测
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
# 测试入口
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # 【DEBUG】开发调试使用，记录细节和变量；生产环境通常关闭
    logger.debug("【调试】进入主程序入口，开始初始化日志")

    # 【INFO】正常流程日志，用于记录程序运行状态
    logger.info("【信息】logger.py内部调用 (仅测试，业务模块调用会显示正确文件名)")

    print(f"日志文件输出路径：{LOG_FILE_PATH}")

    # 【WARNING】警告信息，通常不影响运行，但需要关注
    logger.warning("【警告】未读取到自定义配置，使用默认配置")

    # 【ERROR】当前功能出错，程序通常不会崩溃，但业务已失败
    logger.error("【错误】logger.py内部调用 (仅测试，业务模块调用会显示正确文件名)")

    # 【EXCEPTION】必须在 except 块中调用，自动打印完整异常堆栈，便于定位问题
    try:
        result = 10 / 0
        logger.info(f"【信息】业务计算结果：{result}")
    except Exception:
        logger.exception("【异常】捕获到业务异常，输出完整堆栈信息")
