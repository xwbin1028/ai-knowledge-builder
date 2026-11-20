"""
HTTP 协议常量.

只放协议层状态码, 业务码放各自服务的 *_constants.py.
"""
from typing import Final

HTTP_STATUS_OK: Final[int] = 200

# 5xx 服务端异常区间, 含起点不含终点
HTTP_STATUS_SERVER_ERROR_START: Final[int] = 500
HTTP_STATUS_SERVER_ERROR_END: Final[int] = 600
