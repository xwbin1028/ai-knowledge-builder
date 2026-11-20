"""
MinerU 文档解析常量.

运行参数 接口路径 业务状态码 JSON 键名 输出文件名, 全部只在这里定义.
"""
from typing import Final

# ---------------------------------------------------------------------------
# 运行参数
# ---------------------------------------------------------------------------
# 模型版本: vlm 适合 PDF 图片高精度解析
MINERU_MODEL_VERSION: Final[str] = "vlm"

# 轮询超时, 秒
MINERU_POLL_TIMEOUT_SECONDS: Final[int] = 600

# 轮询间隔, 秒
MINERU_POLL_INTERVAL_SECONDS: Final[int] = 3

# 单次 HTTP 请求超时, 秒
MINERU_DOWNLOAD_TIMEOUT_SECONDS: Final[int] = 300

# ---------------------------------------------------------------------------
# 接口协议
# ---------------------------------------------------------------------------
# 业务成功码
MINERU_API_SUCCESS_CODE: Final[int] = 0

# 业务失败码兜底值
MINERU_API_ERROR_CODE: Final[int] = -1

# 申请上传链接
MINERU_BATCH_UPLOAD_PATH: Final[str] = "/file-urls/batch"

# 查询解析结果
MINERU_BATCH_EXTRACT_RESULTS_PATH: Final[str] = "/extract-results/batch/"

# ---------------------------------------------------------------------------
# 解析状态
# ---------------------------------------------------------------------------
MINERU_STATE_FAILED: Final[str] = "failed"
MINERU_STATE_RUNNING: Final[str] = "running"
MINERU_STATE_PENDING: Final[str] = "pending"
MINERU_STATE_WAITING_FILE: Final[str] = "waiting-file"
MINERU_STATE_CONVERTING: Final[str] = "converting"
MINERU_STATE_DONE: Final[str] = "done"

# 处理中的状态, 用于继续轮询
MINERU_RUNNING_STATES: Final[tuple[str, ...]] = (
    MINERU_STATE_RUNNING,
    MINERU_STATE_PENDING,
    MINERU_STATE_WAITING_FILE,
    MINERU_STATE_CONVERTING,
)

# ---------------------------------------------------------------------------
# JSON 响应键名
# ---------------------------------------------------------------------------
JSON_KEY_CODE: Final[str] = "code"
JSON_KEY_DATA: Final[str] = "data"
JSON_KEY_BATCH_ID: Final[str] = "batch_id"
JSON_KEY_FILE_URLS: Final[str] = "file_urls"
JSON_KEY_EXTRACT_RESULT: Final[str] = "extract_result"
JSON_KEY_STATE: Final[str] = "state"
JSON_KEY_FULL_ZIP_URL: Final[str] = "full_zip_url"

# ---------------------------------------------------------------------------
# 输出文件
# ---------------------------------------------------------------------------
# 下载的解析包重命名后缀
MINERU_OUTPUT_ZIP_RENAME_SUFFIX: Final[str] = "_mineru_output.zip"

# 解析结果中的通用 Markdown 文件名
MINERU_FULL_FILE_STEM: Final[str] = "full"

# 解压后的图片目录名
MINERU_OUTPUT_ZIP_IMAGES_DIR: Final[str] = "images"

# 图片上下文的截取字符数
IMAGE_CONTEXT_CHAR_LENGTH: Final[int] = 100
