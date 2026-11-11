"""
配置读取公共工具，统一处理 .env 加载与环境变量类型转换
封装原生 os.getenv，提供类型安全的环境变量读取方法，解决原生读取永远返回字符串或 None 的问题
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

# 模块加载时自动读取 .env 文件
load_dotenv()

# ---------------------------------------------------------------------------
# 全局常量
# ---------------------------------------------------------------------------
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


# ---------------------------------------------------------------------------
# 配置读取方法
# ---------------------------------------------------------------------------
def env_str(name: str, default: str = "") -> str:
    """
    读取字符串配置。

    Args:
        name (str): 环境变量名称。
        default (str): 变量不存在时的默认值，默认为空字符串。

    Returns:
        str: 读取到的字符串值。
    """
    value = os.getenv(name)
    return value if value is not None else default


def env_bool(name: str, default: bool = False) -> bool:
    """
    读取布尔配置，兼容常见的真假值写法。
    通过白名单匹配的方式，将字符串转换为布尔值。
    如果环境变量不存在、为空或不在白名单内，则返回默认值。

    Args:
        name (str): 环境变量名称。
        default (bool): 变量不存在或无法识别时的默认值。

    Returns:
        bool: 转换后的布尔值。
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
    读取浮点数配置。
    如果环境变量不存在、为空或无法转换为浮点数
    则返回默认值，防止因配置格式错误导致应用启动崩溃。

    Args:
        name (str): 环境变量名称。
        default (float): 变量不存在、为空或格式非法时的默认值。

    Returns:
        float: 转换后的浮点数值。
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default
