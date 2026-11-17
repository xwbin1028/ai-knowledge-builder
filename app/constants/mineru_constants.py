"""
MinerU 解析服务配置与常量模块。

集中管理 MinerU 服务的运行参数（模型版本、超时时间、轮询间隔）
以及接口交互过程中的协议常量（HTTP 状态码、业务返回码、请求路径、业务状态）。
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

# HTTP 5xx 服务端错误状态码范围
HTTP_STATUS_SERVER_ERROR_START: Final[int] = 500
HTTP_STATUS_SERVER_ERROR_END: Final[int] = 600

# --- MinerU 业务层 ---
# MinerU 业务层成功返回码
MINERU_API_SUCCESS_CODE: Final[int] = 0

# MinerU 业务层错误/缺失返回码兜底值
MINERU_API_ERROR_CODE: Final[int] = -1

# --- 接口路径 ---
# MinerU 批量上传文件获取 URL 的接口路径
MINERU_BATCH_UPLOAD_PATH: Final[str] = "/file-urls/batch"

# MinerU 批量获取解析结果 URL 的接口路径
MINERU_BATCH_EXTRACT_RESULTS_PATH: Final[str] = "/extract-results/batch/"

# --- MinerU 解析状态 ---
MINERU_STATE_FAILED: Final[str] = "failed"
MINERU_STATE_RUNNING: Final[str] = "running"
MINERU_STATE_PENDING: Final[str] = "pending"
MINERU_STATE_WAITING_FILE: Final[str] = "waiting-file"
MINERU_STATE_CONVERTING: Final[str] = "converting"

# 处于处理中的状态集合
MINERU_RUNNING_STATES: Final[tuple[str, ...]] = (
    MINERU_STATE_RUNNING,
    MINERU_STATE_PENDING,
    MINERU_STATE_WAITING_FILE,
    MINERU_STATE_CONVERTING
)

# --- JSON 响应体键名 ---
# 统一提取键名，防止在代码中写错魔法字符串
JSON_KEY_CODE: Final[str] = "code"
JSON_KEY_DATA: Final[str] = "data"
JSON_KEY_BATCH_ID: Final[str] = "batch_id"
JSON_KEY_FILE_URLS: Final[str] = "file_urls"
JSON_KEY_EXTRACT_RESULT: Final[str] = "extract_result"
JSON_KEY_STATE: Final[str] = "state"
JSON_KEY_MINERU_ZIP_URL: Final[str] = "mineru_zip_url"  # 如果这是接口返回字段名，保留在这里


# ===========================================================================
# 3. MinerU 专属文件命名常量
# ===========================================================================
# MinerU 解析结果输出压缩包重命名后缀
MINERU_OUTPUT_ZIP_RENAME_SUFFIX: Final[str] = "_mineru_output.zip"

MINERU_FULL_FILE_STEM: Final[str] = "full"
