"""
PDF 解析服务模块。

纯函数服务，调用 MinerU 文档解析服务，下载并解压解析结果，
提取 Markdown 路径与正文内容回写到图状态。
"""
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log, PROJECT_ROOT
from app.constants.file_constants import DEFAULT_OUTPUT_DIR_NAME
from app.infra.config.providers import infra_config
from app.constants.mineru_constants import *
from requests.models import Response
from pathlib import Path
from typing import Any
import requests
import time


def parse_pdf_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 解析服务主入口。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """

    # 1. 进行参数合理性校验
    pdf_path_po, local_file_dir_po = validates_pdf_paths(state)
    # 2. 向minerU申请文件上传地址和batch_id
    mineru_batch_id, upload_mineru_file_url = apply_mineru_get_upload_url(state, pdf_path_po.name)
    # 3. 向指定的文件地址(预签名地址)上传文件数据
    upload_file_to_url(state, pdf_path_po, upload_mineru_file_url)
    # 4. 轮询获取解析结果
    full_zip_url: str = poll_mineru_zip_url(state, mineru_batch_id)
    print(full_zip_url)
    return state


@function_log(
    func_name="轮询 MinerU 解析结果",
    return_names=["full_zip_url"]
)
def poll_mineru_zip_url(state: ImportGraphState, batch_id: str) -> str:
    """
    核心功能：轮询获取 MinerU 解析结果的 ZIP 下载链接

    业务逻辑：
    1. 配置请求路径(request_mineru_url)与请求头(request_mineru_header)
    2. 记录开始时间(start_time)，开启循环轮询
    3. 获取轮询器已运行总时长(polling_run_time)
    4. 判断轮询总时长是否超过最大等待时间(MINERU_POLL_TIMEOUT_SECONDS)
    5. 发送(get)请求获取响应(resp)
    6. 判断网络协议响应状态码(status_code)
    7. 判断接口响应状态码(code)
    8. 获取(mineru)响应结果(extract_result_list)
    9. 判断提取结果(extract_result_list)是否合法
    10. 判断解析状态(resp_json_data_extract_result_state)并处理
    11. 获取并返回解析结果下载链接(full_zip_url)

    Args:
        (state)流程全局状态
        (batch_id)MinerU 接口返回的批次 ID

    Returns:
        (full_zip_url)MinerU 解析结果的 ZIP 下载链接

    Raises:
        TimeoutError: 当轮询总时长超过最大等待时间时抛出
        RuntimeError: 当网络请求异常、HTTP 状态码异常、业务报错或解析失败时抛出
    """
    # 1. 配置请求路径(request_mineru_url)与请求头(request_mineru_header)
    task_id: str = state.get("task_id", "") or ""
    request_mineru_url: str = f"{infra_config.mineru.base_url}{MINERU_BATCH_EXTRACT_RESULTS_PATH}{batch_id}"
    request_mineru_header: dict[str, Any] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {infra_config.mineru.api_key}"
    }

    # 2. 记录开始时间(start_time)，开启循环轮询
    start_time: float = time.time()

    while True:
        # 3. 获取轮询器已运行总时长(polling_run_time)
        polling_run_time: float = time.time() - start_time

        # 4. 判断轮询总时长(polling_run_time)超过最大等待时间(MINERU_POLL_TIMEOUT_SECONDS)
        if polling_run_time >= MINERU_POLL_TIMEOUT_SECONDS:
            logger.error(f"task_id({task_id})【业务终止】-|-轮询 MinerU 解析结果超时,耗时({polling_run_time:.1f}s)")
            raise TimeoutError(f"task_id({task_id})【业务终止】-|-轮询 MinerU 解析结果超时,耗时({polling_run_time:.1f}s)")

        # 5. 发送(get)请求获取响应(resp)
        resp: Response = requests.get(url=request_mineru_url,
                                      headers=request_mineru_header,
                                      timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)

        # 6. 判断网络协议响应状态码(status_code)
        status_code: int = resp.status_code
        if status_code != HTTP_STATUS_OK:
            # MinerU 服务器问题(5xx)
            if HTTP_STATUS_SERVER_ERROR_START <= status_code < HTTP_STATUS_SERVER_ERROR_END:
                logger.warning(f"task_id({task_id})【业务警告】-|-MinerU 服务端异常,稍后重试 status_code({status_code})")
                time.sleep(MINERU_POLL_INTERVAL_SECONDS)
                continue
            # 本地代码问题或其他客户端问题
            logger.error(
                f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")
            raise RuntimeError(
                f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")

        # 7. 判断接口响应状态码(code)
        resp_json: dict[str, Any] = resp.json()
        resp_json_code: int = resp_json.get(JSON_KEY_CODE, MINERU_API_ERROR_CODE)
        if resp_json_code != MINERU_API_SUCCESS_CODE:
            logger.error(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")
            raise RuntimeError(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")

        # 8. 获取(mineru)响应结果(resp_json_data_extract_result)(resp_json_data_extract_result_state)
        resp_json_data: dict[str, Any] = resp_json.get(JSON_KEY_DATA, {})
        extract_result_list: list[dict[str, Any]] = resp_json_data.get(JSON_KEY_EXTRACT_RESULT, [])

        # 9. 判断(extract_result_list)
        if not isinstance(extract_result_list, list) or not extract_result_list:
            logger.error(
                f"task_id({task_id})【业务终止】-|-MinerU 接口未返回合法的 extract_result_list({extract_result_list})")
            raise RuntimeError(
                f"task_id({task_id})【业务终止】-|-MinerU 接口未返回合法的 extract_result_list({extract_result_list})")

        resp_json_data_extract_result: dict[str, Any] = extract_result_list[0]
        resp_json_data_extract_result_state: str = resp_json_data_extract_result.get(JSON_KEY_STATE, "")

        # 10. 判断(resp_json_data_extract_result_state)
        if resp_json_data_extract_result_state == MINERU_STATE_FAILED:
            # 解析失败了
            logger.error(
                f"task_id({task_id})【业务终止】-|-MinerU 解析文件失败 resp_json_data_extract_result({resp_json_data_extract_result})")
            raise RuntimeError(
                f"task_id({task_id})【业务终止】-|-MinerU 解析文件失败 resp_json_data_extract_result({resp_json_data_extract_result})")
        if resp_json_data_extract_result_state in MINERU_RUNNING_STATES:
            # 正在解析中
            logger.info(
                f"task_id({task_id})【业务提示】-|-MinerU 正在解析中，等待重试 resp_json_data_extract_result({resp_json_data_extract_result})")
            time.sleep(MINERU_POLL_INTERVAL_SECONDS)
            continue

        # 11. 获取并返回解析结果下载链接(full_zip_url)
        full_zip_url: str = resp_json_data_extract_result.get(JSON_KEY_FULL_ZIP_URL, "")

        if not isinstance(full_zip_url, str) or not full_zip_url.strip():
            logger.error(
                f"task_id({task_id})【业务终止】-|-MinerU 解析完成但未返回合法的下载链接 full_zip_url({full_zip_url})")
            raise RuntimeError(
                f"task_id({task_id})【业务终止】-|-MinerU 解析完成但未返回合法的下载链接 full_zip_url({full_zip_url})")

        return full_zip_url


@function_log(func_name="上传文件至预签名 URL")
def upload_file_to_url(state: ImportGraphState, pdf_path_po: Path, upload_mineru_file_url: str) -> None:
    """
    核心功能：上传文件至预签名 URL

    业务逻辑：
        1. 读取本地 PDF 文件的二进制内容
        2. 发送(put)请求至预签名(upload_mineru_file_url)
        3. 判断网络协议响应状态码(status_code)

    Args:
        (state)流程全局状态
        (pdf_path_po)上传的 PDF 文件的 Path 对象
        (upload_mineru_file_url)MinerU 接口返回的预签名上传链接

    Raises:
        RuntimeError: 当文件读取失败、网络请求异常，或响应状态码非成功状态时抛出
    """
    # 1. 读取本地 PDF 文件的二进制内容
    task_id: str = state.get("task_id", "") or ""
    upload_mineru_data: bytes = pdf_path_po.read_bytes()

    # 2. 发送(put)请求至预签名(upload_mineru_file_url)
    with requests.Session() as session:
        session.trust_env = False
        resp: Response = session.put(url=upload_mineru_file_url,
                                     data=upload_mineru_data,
                                     timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)

    # 3. 判断网络协议响应状态码(status_code)
    status_code: int = resp.status_code
    if status_code != HTTP_STATUS_OK:
        logger.error(
            f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")
        raise RuntimeError(
            f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")


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
        4. 发送(post)请求获取响应(resp)
        5. 判断网络协议响应状态码(status_code)
        6. 判断接口响应状态码(code)
        7. 返回获取(mineru)响应结果(mineru_batch_id)(upload_mineru_file_url)

    Args:
        (state)流程全局状态
        (pdf_file_name)待上传的 PDF 文件名。

    Returns:
        tuple[(mineru_batch_id) mineru 的批次 ID, (upload_mineru_file_url)文件上传链接]。

    Raises:
        RuntimeError: 当 HTTP 状态码非 200，或业务状态码非成功状态时抛出。
    """
    # 1. 配置请求头(request_mineru_header)
    task_id: str = state.get("task_id", "") or ""
    request_mineru_header: dict[str, Any] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {infra_config.mineru.api_key}"
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

    # 4. 发送(post)请求获取响应(resp)
    resp: Response = requests.post(url=request_mineru_url,
                                   headers=request_mineru_header,
                                   json=request_mineru_data,
                                   timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)

    # 4. 判断网络协议响应状态码(status_code)
    status_code: int = resp.status_code
    if status_code != HTTP_STATUS_OK:
        logger.error(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")
        raise RuntimeError(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口 HTTP 状态码异常 status_code({status_code})")

    # 5. 判断接口响应状态码(code)
    resp_json: dict[str, Any] = resp.json()
    resp_json_code: int = resp_json.get(JSON_KEY_CODE, MINERU_API_ERROR_CODE)
    if resp_json_code != MINERU_API_SUCCESS_CODE:
        logger.error(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")
        raise RuntimeError(f"task_id({task_id})【业务终止】-|-请求 MinerU 接口业务报错 code({resp_json_code})")

    # 6. 获取(mineru)响应结果(mineru_batch_id)(upload_mineru_file_url)
    resp_json_data: dict[str, Any] = resp_json.get(JSON_KEY_DATA, {})
    mineru_batch_id: str = resp_json_data.get(JSON_KEY_BATCH_ID)
    upload_mineru_file_url: str = resp_json_data.get(JSON_KEY_FILE_URLS)[0]

    return mineru_batch_id, upload_mineru_file_url

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


if __name__ == "__main__":
    from app.process.import_.agent.state import create_default_state
    from app.process.import_.agent.nodes.node_pdf_to_md import node_pdf_to_md
    import os

    logger.info("===== 开始 node_pdf_to_md 节点联调测试 =====")

    test_pdf_path = os.path.join(PROJECT_ROOT, "doc", "hak180使用说明书.pdf")
    test_state = create_default_state(
        task_id="test_pdf2md_task_001",
        pdf_path=test_pdf_path,
        local_file_dir=os.path.join(PROJECT_ROOT, "output"),
    )

    result = node_pdf_to_md(test_state)

