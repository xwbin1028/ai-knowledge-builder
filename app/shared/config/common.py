"""
.env 读取工具.

统一 load_dotenv 与类型转换, 业务侧不要直接 os.getenv.
"""
import os

from dotenv import load_dotenv

# 模块加载即读取 .env, override=True 表示以 .env 为准
load_dotenv(override=True)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_TRUE_VALUES: set[str] = {"1", "true", "yes", "on"}
_FALSE_VALUES: set[str] = {"0", "false", "no", "off"}


# ---------------------------------------------------------------------------
# 读取方法
# ---------------------------------------------------------------------------
def env_str(name: str, default: str = "") -> str:
    """
    读取字符串配置.

    Args:
        name: 环境变量名.
        default: 变量缺失时的默认值.

    Returns:
        str: 配置值.
    """
    value = os.getenv(name)
    return value if value is not None else default


def env_bool(name: str, default: bool = False) -> bool:
    """
    读取布尔配置, 兼容常见真假写法.

    变量缺失 为空 或不在白名单内时返回默认值.

    Args:
        name: 环境变量名.
        default: 无法识别时的默认值.

    Returns:
        bool: 转换后的布尔值.
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def env_float(name: str, default: float = 0.0) -> float:
    """
    读取浮点配置.

    变量缺失 为空或格式非法时返回默认值, 避免启动崩溃.

    Args:
        name: 环境变量名.
        default: 兜底值.

    Returns:
        float: 转换后的浮点值.
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default


def env_int(name: str, default: int = 0) -> int:
    """
    读取整数配置.

    变量缺失 为空或格式非法时返回默认值.

    Args:
        name: 环境变量名.
        default: 兜底值.

    Returns:
        int: 转换后的整数值.
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return int(value)
    except ValueError:
        return default
