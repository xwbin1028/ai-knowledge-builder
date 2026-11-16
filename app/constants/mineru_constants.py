"""
MinerU 解析服务配置与常量模块。

集中管理 MinerU 服务的运行参数（模型版本、超时时间、轮询间隔）
以及接口交互过程中的协议常量（HTTP 状态码、业务返回码、请求路径）。
"""
from typing import Final

# ===========================================================================
# 1. 运行配置项
# ===========================================================================

# MinerU 模型版本配置
# vlm 表示视觉语言模型，适合 PDF 图片高精度解析
MINERU_MODEL_VERSION: Final[str] = "vlm"

# MinerU 任务轮询最大超时时间，单位秒
# 600 秒即 10 分钟，超过此时间任务被视为超时
MINERU_POLL_TIMEOUT_SECONDS: Final[int] = 600

# MinerU 任务轮询间隔时间，单位秒
# 每 3 秒向 MinerU 查询一次任务状态
MINERU_POLL_INTERVAL_SECONDS: Final[int] = 3

# MinerU 文件下载超时时间，单位秒
# 300 秒即 5 分钟，用于 requests 的 timeout 参数
MINERU_DOWNLOAD_TIMEOUT_SECONDS: Final[int] = 300


# ===========================================================================
# 2. 接口协议与请求常量
# ===========================================================================

# --- HTTP 协议层 ---
# HTTP 协议层成功状态码
HTTP_STATUS_OK: Final[int] = 200

# --- MinerU 业务层 ---
# MinerU 业务层成功返回码
MINERU_API_SUCCESS_CODE: Final[int] = 0

# MinerU 业务层错误/缺失返回码兜底值
MINERU_API_ERROR_CODE: Final[int] = -1

# --- 接口路径 ---
# MinerU 批量上传文件获取 URL 的接口路径
MINERU_BATCH_UPLOAD_PATH: Final[str] = "/file-urls/batch"