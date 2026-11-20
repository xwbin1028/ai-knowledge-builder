"""
PDF 解析服务.

调用 MinerU 全链路: 申请上传链接 -> 上传 PDF -> 轮询结果 -> 下载解压 -> 提取 md.
"""
import shutil
import time
from pathlib import Path
from typing import Any

import requests
from requests.models import Response

from app.constants.file_constants import DEFAULT_OUTPUT_DIR_NAME, GLOB_MD_FILES, MD_SUFFIX
from app.constants.http_constants import (
    HTTP_STATUS_OK,
    HTTP_STATUS_SERVER_ERROR_END,
    HTTP_STATUS_SERVER_ERROR_START,
)
from app.constants.mineru_constants import (
    JSON_KEY_BATCH_ID,
    JSON_KEY_CODE,
    JSON_KEY_DATA,
    JSON_KEY_EXTRACT_RESULT,
    JSON_KEY_FILE_URLS,
    JSON_KEY_FULL_ZIP_URL,
    JSON_KEY_STATE,
    MINERU_API_ERROR_CODE,
    MINERU_API_SUCCESS_CODE,
    MINERU_BATCH_EXTRACT_RESULTS_PATH,
    MINERU_BATCH_UPLOAD_PATH,
    MINERU_DOWNLOAD_TIMEOUT_SECONDS,
    MINERU_FULL_FILE_STEM,
    MINERU_MODEL_VERSION,
    MINERU_OUTPUT_ZIP_RENAME_SUFFIX,
    MINERU_POLL_INTERVAL_SECONDS,
    MINERU_POLL_TIMEOUT_SECONDS,
    MINERU_RUNNING_STATES,
    MINERU_STATE_DONE,
    MINERU_STATE_FAILED,
)
from app.infra.config.providers import infra_config
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import PROJECT_ROOT, function_log, logger


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="PDF 解析主入口", return_names=["state"])
def parse_pdf_to_markdown(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 解析主入口, MinerU 全链路.

    业务逻辑:
        1. 校验 pdf 路径与输出目录, 得到 pdf_path_po 与 local_file_dir_po
        2. 申请上传链接, 得到 batch_id 与 upload_url
        3. 上传 PDF 到 upload_url
        4. 轮询解析结果, 得到 zip_url
        5. 下载解压, 得到 md_path
        6. 回写 state["md_path"]

    Args:
        state: 图全局状态, 需含 task_id 与 pdf_path.

    Returns:
        ImportGraphState: 已写入 md_path 的状态.

    Raises:
        ValueError: pdf_path 非法.
        FileNotFoundError: pdf 文件不存在.
        TimeoutError: 轮询超时.
        RuntimeError: 接口异常或解压失败.
    """
    task_id: str = state.get("task_id", "")

    # 1. 校验 pdf 路径与输出目录
    pdf_path_po, local_file_dir_po = validate_pdf_paths(state)

    # 2. 申请上传链接
    batch_id, upload_url = request_mineru_upload_url(state, pdf_path_po.name)

    # 3. 上传 PDF
    upload_file_to_url(state, pdf_path_po, upload_url)

    # 4. 轮询解析结果
    zip_url = poll_mineru_zip_url(state, batch_id)

    # 5. 下载解压
    md_path = download_and_extract_md(state, zip_url, local_file_dir_po, pdf_path_po.stem)

    # 6. 回写 state
    state["md_path"] = md_path
    return state


# ---------------------------------------------------------------------------
# 路径校验
# ---------------------------------------------------------------------------
@function_log(func_name="校验 pdf 路径并确保输出目录可用", return_names=["pdf_path_po", "local_file_dir_po"])
def validate_pdf_paths(state: ImportGraphState) -> tuple[Path, Path]:
    """
    校验 pdf 路径并确保输出目录可用.

    业务逻辑:
        1. 从 state 取 local_file_dir 与 pdf_path
        2. 校验 pdf_path 为非空字符串
        3. 输出目录非法时用默认 output
        4. 转 Path 并校验 pdf 文件存在
        5. 输出目录不存在则创建

    Args:
        state: 图全局状态.

    Returns:
        tuple[Path, Path]: pdf 文件与输出目录.

    Raises:
        ValueError: pdf_path 非法.
        FileNotFoundError: pdf 文件不存在或不是常规文件.
    """
    # 1. 从 state 取 local_file_dir 与 pdf_path
    task_id: str = state.get("task_id", "")
    local_file_dir: Any = state.get("local_file_dir")
    pdf_path: Any = state.get("pdf_path")

    # 2. 校验 pdf_path 为非空字符串
    if not isinstance(pdf_path, str) or not pdf_path.strip():
        raise business_error(ValueError, task_id, "PDF 路径非法", pdf_path=pdf_path)

    # 3. 输出目录非法时用默认 output
    if not isinstance(local_file_dir, str) or not local_file_dir.strip():
        local_file_dir = str(PROJECT_ROOT / DEFAULT_OUTPUT_DIR_NAME)
        logger.warning(f"[警告] task_id={task_id} | 输出目录非法, 用默认值 | dir={local_file_dir}")
        state["local_file_dir"] = local_file_dir

    # 4. 转 Path 并校验 pdf 文件存在
    pdf_path_po: Path = Path(pdf_path)
    local_file_dir_po: Path = Path(local_file_dir)
    if not pdf_path_po.is_file():
        raise business_error(FileNotFoundError, task_id, "PDF 文件不存在或不是常规文件", pdf_path=pdf_path_po)

    # 5. 输出目录不存在则创建
    if not local_file_dir_po.is_dir():
        logger.warning(f"[警告] task_id={task_id} | 输出目录不存在, 自动创建 | dir={local_file_dir_po}")
        local_file_dir_po.mkdir(parents=True, exist_ok=True)

    return pdf_path_po, local_file_dir_po


# ---------------------------------------------------------------------------
# MinerU 接口
# ---------------------------------------------------------------------------
@function_log(func_name="获取 MinerU 上传链接", return_names=["batch_id", "upload_url"])
def request_mineru_upload_url(state: ImportGraphState, pdf_file_name: str) -> tuple[str, str]:
    """
    申请文件预签名上传链接.

    业务逻辑:
        1. 组装请求头 请求体 请求地址
        2. POST 获取响应
        3. 校验 HTTP 状态码
        4. 校验业务码
        5. 取 batch_id 与 upload_url 并校验

    Args:
        state: 图全局状态.
        pdf_file_name: 待上传的 PDF 文件名.

    Returns:
        tuple[str, str]: 批次 ID 与上传链接.

    Raises:
        RuntimeError: HTTP 异常 业务报错或响应缺字段.
    """
    # 1. 组装请求头 请求体 请求地址
    task_id: str = state.get("task_id", "")
    request_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {infra_config.mineru.api_key}",
    }
    request_payload: dict[str, Any] = {
        "files": [{"name": pdf_file_name}],
        "model_version": MINERU_MODEL_VERSION,
        "extra_formats": ["html"],
    }
    request_url: str = f"{infra_config.mineru.base_url}{MINERU_BATCH_UPLOAD_PATH}"

    # 2. POST 获取响应
    resp: Response = requests.post(
        url=request_url,
        headers=request_headers,
        json=request_payload,
        timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS,
    )

    # 3. 校验 HTTP 状态码
    if resp.status_code != HTTP_STATUS_OK:
        raise business_error(RuntimeError, task_id, "申请上传链接 HTTP 异常", status_code=resp.status_code)

    # 4. 校验业务码
    resp_json: dict[str, Any] = resp.json()
    resp_code: int = resp_json.get(JSON_KEY_CODE, MINERU_API_ERROR_CODE)
    if resp_code != MINERU_API_SUCCESS_CODE:
        raise business_error(RuntimeError, task_id, "申请上传链接业务报错", code=resp_code)

    # 5. 取 batch_id 与 upload_url 并校验
    resp_data: dict[str, Any] = resp_json.get(JSON_KEY_DATA, {})
    batch_id: str = resp_data.get(JSON_KEY_BATCH_ID) or ""
    file_urls: list[str] = resp_data.get(JSON_KEY_FILE_URLS) or []
    if not batch_id or not file_urls:
        raise business_error(
            RuntimeError, task_id, "上传链接响应缺字段", batch_id=batch_id, file_urls=file_urls
        )

    return batch_id, file_urls[0]


@function_log(func_name="上传文件至预签名 URL")
def upload_file_to_url(state: ImportGraphState, pdf_path_po: Path, upload_url: str) -> None:
    """
    上传 PDF 到预签名地址.

    业务逻辑:
        1. 读取 PDF 二进制
        2. PUT 到 upload_url
        3. 校验 HTTP 状态码

    Args:
        state: 图全局状态.
        pdf_path_po: 本地 PDF 文件.
        upload_url: 预签名上传链接.

    Raises:
        RuntimeError: HTTP 状态码非 200.
    """
    # 1. 读取 PDF 二进制
    task_id: str = state.get("task_id", "")
    pdf_bytes: bytes = pdf_path_po.read_bytes()

    # 2. PUT 到 upload_url, trust_env=False 表示不走系统代理
    with requests.Session() as session:
        session.trust_env = False
        resp: Response = session.put(
            url=upload_url,
            data=pdf_bytes,
            timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS,
        )

    # 3. 校验 HTTP 状态码
    if resp.status_code != HTTP_STATUS_OK:
        raise business_error(RuntimeError, task_id, "上传 PDF HTTP 异常", status_code=resp.status_code)


@function_log(func_name="轮询 MinerU 解析结果", return_names=["zip_url"])
def poll_mineru_zip_url(state: ImportGraphState, batch_id: str) -> str:
    """
    轮询解析结果直到完成.

    业务逻辑:
        1. 组装请求地址与请求头
        2. 每轮先判超时, 超时则终止
        3. 请求解析结果并校验 HTTP 状态码, 5xx 重试
        4. 校验业务码
        5. 取解析结果并校验非空
        6. 按状态处理: 失败终止 处理中等待 完成返回

    Args:
        state: 图全局状态.
        batch_id: MinerU 批次 ID.

    Returns:
        str: 解析结果 ZIP 下载链接.

    Raises:
        TimeoutError: 轮询超时.
        RuntimeError: 接口异常或解析失败.
    """
    # 1. 组装请求地址与请求头
    task_id: str = state.get("task_id", "")
    request_url: str = (
        f"{infra_config.mineru.base_url}{MINERU_BATCH_EXTRACT_RESULTS_PATH}{batch_id}"
    )
    request_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {infra_config.mineru.api_key}",
    }
    start_ts: float = time.time()

    while True:
        # 2. 每轮先判超时
        elapsed_s: float = time.time() - start_ts
        if elapsed_s >= MINERU_POLL_TIMEOUT_SECONDS:
            raise business_error(
                TimeoutError, task_id, "轮询 MinerU 超时", elapsed_s=f"{elapsed_s:.1f}"
            )

        # 3. 请求解析结果并校验 HTTP 状态码
        resp: Response = requests.get(
            url=request_url,
            headers=request_headers,
            timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS,
        )
        status_code: int = resp.status_code
        if status_code != HTTP_STATUS_OK:
            # 服务端 5xx 可重试, 其他状态码直接终止
            if HTTP_STATUS_SERVER_ERROR_START <= status_code < HTTP_STATUS_SERVER_ERROR_END:
                logger.warning(
                    f"[警告] task_id={task_id} | MinerU 服务端异常, 稍后重试 | status_code={status_code}"
                )
                time.sleep(MINERU_POLL_INTERVAL_SECONDS)
                continue
            raise business_error(RuntimeError, task_id, "查询解析结果 HTTP 异常", status_code=status_code)

        # 4. 校验业务码
        resp_json: dict[str, Any] = resp.json()
        resp_code: int = resp_json.get(JSON_KEY_CODE, MINERU_API_ERROR_CODE)
        if resp_code != MINERU_API_SUCCESS_CODE:
            raise business_error(RuntimeError, task_id, "查询解析结果业务报错", code=resp_code)

        # 5. 取解析结果并校验非空
        resp_data: dict[str, Any] = resp_json.get(JSON_KEY_DATA, {})
        extract_result_list = resp_data.get(JSON_KEY_EXTRACT_RESULT)
        if not isinstance(extract_result_list, list) or not extract_result_list:
            raise business_error(
                RuntimeError, task_id, "解析结果为空", extract_result=extract_result_list
            )

        # 6. 按状态处理: 失败终止 处理中等待 完成返回
        extract_result: dict[str, Any] = extract_result_list[0]
        extract_state: str = extract_result.get(JSON_KEY_STATE, "")
        if extract_state == MINERU_STATE_FAILED:
            raise business_error(RuntimeError, task_id, "MinerU 解析失败", state=extract_state)

        if extract_state in MINERU_RUNNING_STATES:
            logger.info(f"[提示] task_id={task_id} | MinerU 解析中, 等待重试 | state={extract_state}")
            time.sleep(MINERU_POLL_INTERVAL_SECONDS)
            continue

        if extract_state == MINERU_STATE_DONE:
            zip_url: str = extract_result.get(JSON_KEY_FULL_ZIP_URL) or ""
            if not zip_url:
                raise business_error(RuntimeError, task_id, "解析完成但下载链接为空", state=extract_state)
            logger.info(f"[提示] task_id={task_id} | 解析完成 | zip_url={zip_url}")
            return zip_url

        raise business_error(RuntimeError, task_id, "未知解析状态", state=extract_state)


# ---------------------------------------------------------------------------
# 结果下载
# ---------------------------------------------------------------------------
@function_log(func_name="下载并解压 MinerU 解析结果", return_names=["md_path"])
def download_and_extract_md(
    state: ImportGraphState,
    zip_url: str,
    local_file_dir_po: Path,
    pdf_stem: str,
) -> str:
    """
    下载解析 ZIP, 解压并提取目标 Markdown 路径.

    业务逻辑:
        1. 下载 ZIP 并校验 HTTP 状态码
        2. 写入本地 zip
        3. 清理并重建解压目录
        4. 解压
        5. 收集 md 文件并校验非空
        6. 优先同名文件, 其次 full.md 重命名
        7. 返回 md_path

    Args:
        state: 图全局状态.
        zip_url: 解析结果 ZIP 链接.
        local_file_dir_po: 本地输出目录.
        pdf_stem: 原 PDF 主文件名.

    Returns:
        str: 目标 Markdown 路径.

    Raises:
        RuntimeError: 下载失败 解压失败或找不到 md 文件.
    """
    # 1. 下载 ZIP 并校验 HTTP 状态码
    task_id: str = state.get("task_id", "")
    resp: Response = requests.get(url=zip_url, timeout=MINERU_DOWNLOAD_TIMEOUT_SECONDS)
    if resp.status_code != HTTP_STATUS_OK:
        raise business_error(RuntimeError, task_id, "下载解析包 HTTP 异常", status_code=resp.status_code)

    # 2. 写入本地 zip
    zip_file_po: Path = local_file_dir_po / f"{pdf_stem}{MINERU_OUTPUT_ZIP_RENAME_SUFFIX}"
    zip_file_po.write_bytes(resp.content)

    # 3. 清理并重建解压目录
    zip_dir_po: Path = local_file_dir_po / pdf_stem
    if zip_dir_po.is_dir():
        logger.warning(f"[警告] task_id={task_id} | 解压目录已存在, 重建 | dir={zip_dir_po}")
        shutil.rmtree(zip_dir_po)
    zip_dir_po.mkdir(parents=True, exist_ok=True)

    # 4. 解压
    shutil.unpack_archive(zip_file_po, zip_dir_po)

    # 5. 收集 md 文件并校验非空
    md_file_list: list[Path] = list(zip_dir_po.rglob(GLOB_MD_FILES))
    if not md_file_list:
        raise business_error(RuntimeError, task_id, "解压后没有 Markdown 文件", dir=zip_dir_po)

    # 6. 优先同名文件, 其次 full.md 重命名
    rename_target_po: Path | None = None
    for md_file_po in md_file_list:
        if md_file_po.stem == pdf_stem:
            logger.info(f"[提示] task_id={task_id} | 找到同名 Markdown | md_path={md_file_po}")
            return str(md_file_po)
        if md_file_po.stem == MINERU_FULL_FILE_STEM:
            rename_target_po = md_file_po

    if rename_target_po is None:
        raise business_error(RuntimeError, task_id, "既没有同名文件也没有 full.md", dir=zip_dir_po)

    final_md_po: Path = rename_target_po.with_name(f"{pdf_stem}{MD_SUFFIX}")
    md_path: str = str(rename_target_po.rename(final_md_po))

    # 7. 返回 md_path
    logger.info(f"[提示] task_id={task_id} | full.md 已重命名 | md_path={md_path}")
    return md_path


if __name__ == "__main__":
    # 延迟导入, 避免服务与节点循环依赖
    from app.process.import_.agent.nodes.node_pdf_to_md import node_pdf_to_md
    from app.process.import_.agent.state import create_default_state

    logger.info("[提示] node_pdf_to_md 联调开始")
    pdf_path = str(PROJECT_ROOT / "doc" / "hak180使用说明书.pdf")
    test_state = create_default_state(
        task_id="test_node_pdf_to_md_001",
        pdf_path=pdf_path,
        local_file_dir=str(PROJECT_ROOT / "output"),
    )
    result_state = node_pdf_to_md(test_state)
    logger.info(f"[提示] node_pdf_to_md 联调结束 | md_path={result_state.get('md_path')}")
