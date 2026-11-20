"""
日志组件测试.

运行: .venv/Scripts/python -m test.test_runtime_logger
"""
from app.shared.runtime.logger import LOG_FILE_PATH, logger


if __name__ == "__main__":
    print(f"日志文件路径: {LOG_FILE_PATH}")

    logger.debug("[调试] 日志组件测试")
    logger.info("[提示] 日志组件测试")
    logger.warning("[警告] 日志组件测试")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("[异常] 日志组件堆栈测试")

    print("日志组件测试通过")
