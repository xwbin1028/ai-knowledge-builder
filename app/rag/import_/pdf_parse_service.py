"""
PDF 解析服务模块。

纯函数服务，调用 MinerU 文档解析服务，下载并解压解析结果，
提取 Markdown 路径与正文内容回写到图状态。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log, PROJECT_ROOT
from app.constants.file_constants import DEFAULT_OUTPUT_DIR_NAME
from app.infra.config.providers import infra_config
from app.constants.mineru_constants import MINERU_MODEL_VERSION, MINERU_DOWNLOAD_TIMEOUT_SECONDS, \
    MINERU_BATCH_UPLOAD_PATH, MINERU_API_ERROR_CODE, MINERU_API_SUCCESS_CODE, HTTP_STATUS_OK
from requests.models import Response
from pathlib import Path
from typing import Any
import requests


def parse_pdf_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 解析服务主入口。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state


@function_log(
    func_name="获取 MinerU 上传链接",
    return_names=["mineru_batch_id", "mineru_file_url"]
)
def apply_mineru_get_upload_url(state: ImportGraphState, pdf_file_name: str) -> tuple[str, str]:
    """
    核心功能：获取 MinerU 上传链接

    业务逻辑：
        1. 配置请求头(request_mineru_header)
        2. 配置请求体(request_mineru_data)
        3. 配置请求路径(request_mineru_url)
        4. 发送(post)请求获取响应(response)
        5. 判断网络协议响应状态码(status_code)
        6. 判断接口响应状态码(code)
        7. 返回获取(mineru)响应结果(mineru_batch_id)(mineru_file_url)

    Args:
        (state)流程全局状态
        (pdf_file_name)待上传的 PDF 文件名。

    Returns:
        tuple[(mineru_batch_id) mineru 的批次 ID, (mineru_file_url)文件上传链接]。

    Raises:
        RuntimeError: 当 HTTP 状态码非 200，或业务状态码非成功状态时抛出。
    """
    # 1. 配置请求头(request_mineru_header)
    task_id: str = state.get("task_id", "") or ""
    token: str = infra_config.mineru.api_key
    request_mineru_header: dict[str, Any] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. 配置请求体(request_mineru_data)
    request_mineru_data: dict[str, Any] = {
        "files": [
            {"name": pdf_file_name}
        ],
        "model_version": MINERU_MODEL_VERSION,
        "extra_formats": ["html"]
    }

    # 3. 配置请求路径(request_mineru_url)
    request_mineru_url: str = f"{infra_config.mineru.base_url}{MINERU_BATCH_UPLOAD_PATH}"

    # 4. 发送(post)请求获取响应(response)
    resp: Response = requests.post(
        url=request_mineru_url,
        headers=request_mineru_header,
        json=request_mineru_data,
        timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS
    )

    # 4. 判断网络协议响应状态码(status_code)
    status_code: int = resp.status_code
    if status_code != HTTP_STATUS_OK:
        logger.error(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")
        raise RuntimeError(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")

    # 5. 判断接口响应状态码(code)
    resp_json: dict[str, Any] = resp.json()
    resp_json_code: int = resp_json.get("code", MINERU_API_ERROR_CODE)
    if resp_json_code != MINERU_API_SUCCESS_CODE:
        logger.error(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")
        raise RuntimeError(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")

    # 6. 获取(mineru)响应结果(mineru_batch_id)(mineru_file_url)
    resp_json_data: dict[str, Any] = resp_json.get("data", {})
    mineru_batch_id: str = resp_json_data.get("batch_id")
    mineru_file_url: str = resp_json_data.get("file_urls")[0]

    return mineru_batch_id, mineru_file_url

@function_log(
    func_name="校验 pdf 路径并确保输出目录可用",
    return_names=["pdf_path_po", "local_file_dir_po"]
)
def validates_pdf_paths(state: ImportGraphState) -> tuple[Path, Path]:
    """
    核心功能：校验 pdf 路径并确保输出目录可用

    业务逻辑：
        1. 从(state)中获取输出文件夹的路径(local_file_dir) pdf 文件存储路径(pdf_path)
        2. 判断(pdf_path)
        3. 判断(local_file_dir)
        4. 类型转换(pdf_path: str->pdf_path_po:Path)(local_file_dir: str->local_file_dir_po:Path)
        5. 判断(pdf_path_po)
        6. 判断(local_file_dir_po)
        7. 返回(pdf_path_po)(local_file_dir_po)

    Args:
        (state)流程全局状态

    Returns:
        tuple[(pdf_path_po)pdf存储路径, (local_file_dir_po)输出目录]

    Raises:
        ValueError: 当 state 中的 pdf_path 缺失、不是字符串或为空白字符串时抛出。
        FileNotFoundError: 当 pdf_path 指向的路径不存在，或指向的不是常规文件时抛出。
    """
    # 1. 从(state)中获取输出文件夹的路径(local_file_dir) pdf 文件存储路径(pdf_path)
    task_id: str = state.get("task_id", "") or ""
    local_file_dir: Any = state.get("local_file_dir")
    pdf_path: Any = state.get("pdf_path")

    # 2. 判断(pdf_path)
    if not isinstance(pdf_path, str) or not pdf_path.strip():
        logger.error(f"task_id({task_id})【业务终止】-|-PDF文件存储路径非法 pdf_path({pdf_path})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-PDF文件存储路径非法 pdf_path({pdf_path})")

    # 3. 判断(local_file_dir)
    if not isinstance(local_file_dir, str) or not local_file_dir.strip():
        local_file_dir = str(PROJECT_ROOT / DEFAULT_OUTPUT_DIR_NAME)
        logger.warning(f"task_id({task_id})【业务警告】-|-输出文件夹的路径为空或非法,已配置默认值 local_file_dir({local_file_dir})")
        state["local_file_dir"] = local_file_dir

    # 4. 类型转换(pdf_path: str->pdf_path_po:Path)(local_file_dir: str->local_file_dir_po:Path)
    pdf_path_po: Path = Path(pdf_path)
    local_file_dir_po: Path = Path(local_file_dir)

    # 5. 判断(pdf_path_po)
    if not pdf_path_po.is_file():
        logger.error(f"task_id({task_id})【业务终止】-|-PDF文件不存在或不是常规文件 pdf_path_po({pdf_path_po})")
        raise FileNotFoundError(
            f"task_id({task_id})【业务终止】-|-PDF文件不存在或不是常规文件 pdf_path_po({pdf_path_po})")

    # 6. 判断(local_file_dir_po)
    if not local_file_dir_po.is_dir():
        logger.warning(f"task_id({task_id})【业务警告】-|-输出目录不存在,自动创建 local_file_dir_po({local_file_dir_po})")
        local_file_dir_po.mkdir(parents=True, exist_ok=True)

    # 7. 返回(pdf_path_po)(local_file_dir_po)
    return pdf_path_po, local_file_dir_po
