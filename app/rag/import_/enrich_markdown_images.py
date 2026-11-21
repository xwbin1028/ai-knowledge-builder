"""
Markdown 图片增强服务.

职责: 扫描图片引用, 调视觉模型生成说明, 上传 MinIO 并替换正文地址.
边界: 不生成图片, 不改动正文其他内容; 单张失败时保留可回退的地址与说明.
"""
import base64
import re
from mimetypes import guess_type
from pathlib import Path
from typing import Any

import requests

from app.constants.file_constants import SUPPORTED_IMAGE_SUFFIXES
from app.constants.http_constants import HTTP_STATUS_OK
from app.constants.mineru_constants import IMAGE_CONTEXT_CHAR_LENGTH, MINERU_OUTPUT_ZIP_IMAGES_DIR
from app.constants.prompt_constants import PROMPT_IMAGE_SUMMARY
from app.infra.config.providers import infra_config
from app.infra.minio.minio_gateway import minio_gateway
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.load_prompt import load_prompt
from app.shared.runtime.logger import function_log, logger

# 图片引用: (图片名, 本地图片 Path, (上文, 下文))
ImageRef = tuple[str, Path, tuple[str, str]]

# 视觉模型接口, 与 OpenAI Chat Completions 兼容
_VISION_CHAT_PATH = "/chat/completions"

# 视觉模型单次请求超时, 秒; 图片转 base64 后体积较大, 不宜过短
_VISION_TIMEOUT_SECONDS = 120

# 视觉模型温度兜底值, .env 未配置时使用
_VISION_TEMPERATURE = 0.1


def _build_image_ref_pattern(image_name: str) -> str:
    """拼出匹配单张图片引用的正则, 前后加边界避免 a.png 命中 aa.png."""
    escaped_name = re.escape(image_name)
    return r"!\[.*?\]\([^)]*?(?<![\w.-])" + escaped_name + r"(?![\w.-])[^)]*?\)"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="增强 Markdown 图片", return_names=["state"])
def enrich_markdown_images(state: ImportGraphState) -> ImportGraphState:
    """
    Markdown 图片增强主入口.

    业务逻辑:
        1. 加载并校验 md, 定位图片目录
        2. 图片目录缺失或为空则跳过
        3. 收集图片引用, 无引用则跳过
        4. 调视觉模型生成图片说明, 单张失败用文件名兜底
        5. 上传 MinIO 得到访问 URL
        6. 替换图片地址并保存新 md
        7. 回写 state 的 md_content 与 md_path

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 图片地址已替换, 或原样返回.

    Raises:
        ValueError: md_path 为空.
        FileNotFoundError: md 文件不存在.
    """
    task_id: str = str(state.get("task_id", ""))

    # 1. 加载并校验 md, 定位图片目录
    md_content, md_path_po, image_dir_po = load_markdown(state)

    # 2. 图片目录缺失或为空则跳过
    if image_dir_po is None or not any(image_dir_po.iterdir()):
        logger.info(f"[提示] task_id={task_id} | 无图片, 跳过增强 | md_path={md_path_po}")
        return state

    # 3. 收集图片引用, 无引用则跳过
    image_ref_list: list[ImageRef] = collect_image_refs(state, image_dir_po, md_content)
    if not image_ref_list:
        logger.info(f"[提示] task_id={task_id} | 正文未引用图片, 跳过增强 | md_path={md_path_po}")
        return state

    # 4. 调视觉模型生成图片说明, 单张失败用文件名兜底
    image_desc_map: dict[str, str] = describe_images(state, image_ref_list, md_path_po.stem)

    # 5. 上传 MinIO 得到访问 URL
    image_url_map: dict[str, str] = upload_images_to_minio(state, image_ref_list, md_path_po.stem)
    if not image_url_map:
        logger.warning(f"[警告] task_id={task_id} | 图片全部上传失败, 保留原正文")
        return state

    # 6. 替换图片地址并保存新 md
    enriched_md_content: str = replace_image_refs(md_content, image_url_map, image_desc_map)
    enriched_md_path: str = save_enriched_md(enriched_md_content, md_path_po)

    # 7. 回写 state 的 md_content 与 md_path
    state["md_content"] = enriched_md_content
    state["md_path"] = enriched_md_path

    logger.info(
        f"[提示] task_id={task_id} | 图片增强完成 "
        f"| count={len(image_url_map)} | md_path={enriched_md_path}"
    )
    return state


# ---------------------------------------------------------------------------
# 读取与收集
# ---------------------------------------------------------------------------
@function_log(
    func_name="加载并校验 Markdown 数据",
    return_names=["md_content", "md_path_po", "image_dir_po"],
)
def load_markdown(state: ImportGraphState) -> tuple[str, Path, Path | None]:
    """
    加载并校验 Markdown, 定位图片目录.

    业务逻辑:
        1. 从 state 取 md_path 并校验非空
        2. 转 Path 并校验文件存在
        3. 读取正文并回写 state
        4. 定位图片目录, 不存在时返回 None

    副作用:
        回写 state["md_content"].

    Args:
        state: 图全局状态.

    Returns:
        tuple[str, Path, Path | None]: md 正文, md 文件, 图片目录; 无图片目录时为 None.

    Raises:
        ValueError: md_path 为空.
        FileNotFoundError: md 文件不存在.
    """
    # 1. 从 state 取 md_path 并校验非空
    task_id: str = str(state.get("task_id", ""))
    md_path: str = str(state.get("md_path") or "")
    if not md_path.strip():
        raise business_error(ValueError, task_id, "Markdown 路径为空", md_path=md_path)

    # 2. 转 Path 并校验文件存在
    md_path_po: Path = Path(md_path)
    if not md_path_po.is_file():
        raise business_error(FileNotFoundError, task_id, "Markdown 文件不存在", md_path=md_path_po)

    # 3. 读取正文并回写 state
    md_content: str = md_path_po.read_text(encoding="utf-8")
    state["md_content"] = md_content

    # 4. 定位图片目录, 不存在时返回 None
    image_dir_po: Path = md_path_po.parent / MINERU_OUTPUT_ZIP_IMAGES_DIR
    if not image_dir_po.is_dir():
        return md_content, md_path_po, None
    return md_content, md_path_po, image_dir_po


@function_log(func_name="收集 Markdown 图片引用", return_names=["image_ref_list"])
def collect_image_refs(
    state: ImportGraphState,
    image_dir_po: Path,
    md_content: str,
) -> list[ImageRef]:
    """
    收集图片目录中的引用及上下文.

    业务逻辑:
        1. 遍历图片目录
        2. 过滤非文件与不支持的后缀
        3. 在正文中匹配图片引用
        4. 截取上文与下文
        5. 组装 ImageRef 列表

    Args:
        state: 图全局状态.
        image_dir_po: 图片目录.
        md_content: Markdown 正文.

    Returns:
        list[ImageRef]: 图片名 Path 与上下文.
    """
    # 1. 遍历图片目录
    task_id: str = str(state.get("task_id", ""))
    image_ref_list: list[ImageRef] = []

    for image_path_po in image_dir_po.iterdir():
        # 2. 过滤非文件与不支持的后缀
        if not image_path_po.is_file():
            continue
        if image_path_po.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            logger.debug(
                f"[调试] task_id={task_id} | 跳过不支持的后缀 | file={image_path_po}"
            )
            continue

        image_name: str = image_path_po.name

        # 3. 在正文中匹配图片引用
        image_ref_match = re.search(_build_image_ref_pattern(image_name), md_content)
        if image_ref_match is None:
            logger.debug(f"[调试] task_id={task_id} | 正文未引用该图片 | file={image_name}")
            continue

        # 4. 截取上文与下文
        ref_start: int = image_ref_match.start()
        ref_end: int = image_ref_match.end()
        left_context: str = md_content[
            max(ref_start - IMAGE_CONTEXT_CHAR_LENGTH, 0):ref_start
        ].strip()
        right_context: str = md_content[
            ref_end:min(ref_end + IMAGE_CONTEXT_CHAR_LENGTH, len(md_content))
        ].strip()

        # 5. 组装 ImageRef 列表
        image_ref_list.append((image_name, image_path_po, (left_context, right_context)))

    logger.info(f"[提示] task_id={task_id} | 图片引用收集完成 | count={len(image_ref_list)}")
    return image_ref_list


# ---------------------------------------------------------------------------
# 多模态描述
# ---------------------------------------------------------------------------
@function_log(func_name="调用视觉模型生成图片说明", return_names=["image_desc_map"])
def describe_images(
    state: ImportGraphState,
    image_ref_list: list[ImageRef],
    doc_stem: str,
) -> dict[str, str]:
    """
    调用视觉模型为图片生成文字说明.

    单张图片失败时用文件名兜底, 不中断整篇文档的导入.

    业务逻辑:
        1. 校验视觉模型配置
        2. 遍历图片引用
        3. 渲染提示词并请求视觉模型
        4. 记录说明, 失败则用文件名兜底
        5. 返回图片名到说明的映射

    Args:
        state: 图全局状态.
        image_ref_list: 收集到的图片引用.
        doc_stem: 当前 Markdown 文件名, 不含后缀.

    Returns:
        dict[str, str]: 图片名到说明的映射, 失败的图片说明为文件名.

    Raises:
        ValueError: 视觉模型配置缺失.
    """
    # 1. 校验视觉模型配置
    task_id: str = str(state.get("task_id", ""))
    _validate_vision_config(task_id)

    # 2. 遍历图片引用
    image_desc_map: dict[str, str] = {}
    failed_count: int = 0
    for image_name, image_path_po, image_context in image_ref_list:
        # 3. 渲染提示词并请求视觉模型
        image_prompt: str = load_prompt(
            PROMPT_IMAGE_SUMMARY,
            file_name=doc_stem,
            image_context=image_context,
        )
        try:
            image_desc_map[image_name] = _request_image_description(
                image_name, image_path_po, image_prompt
            )
        except Exception as exc:
            # 4. 记录说明, 失败则用文件名兜底; 单张失败可恢复, 继续下一张
            failed_count += 1
            image_desc_map[image_name] = image_name
            logger.warning(
                f"[警告] task_id={task_id} | 图片说明失败, 用文件名兜底 "
                f"| image={image_name} | error={exc}"
            )

    # 5. 返回图片名到说明的映射
    logger.info(
        f"[提示] task_id={task_id} | 图片说明完成 "
        f"| total={len(image_ref_list)} | failed={failed_count}"
    )
    return image_desc_map


def _validate_vision_config(task_id: str) -> None:
    """校验视觉模型地址 密钥 模型名, 缺失即终止."""
    if not infra_config.llm.base_url:
        raise business_error(ValueError, task_id, "视觉模型配置缺失", field="OPENAI_BASE_URL")
    if not infra_config.llm.api_key:
        raise business_error(ValueError, task_id, "视觉模型配置缺失", field="OPENAI_API_KEY")
    if not infra_config.llm.vl_model:
        raise business_error(ValueError, task_id, "视觉模型配置缺失", field="VL_MODEL")


def _request_image_description(
    image_name: str,
    image_path_po: Path,
    image_prompt: str,
) -> str:
    """
    请求视觉模型生成单张图片说明.

    业务逻辑:
        1. 读取图片并转 base64 数据 URI
        2. 组装请求地址 请求头 请求体
        3. 发送 POST 并校验 HTTP 状态码
        4. 解析响应并校验说明非空

    Args:
        image_name: 图片文件名, 只用于错误信息.
        image_path_po: 本地图片文件.
        image_prompt: 已渲染的图片说明提示词.

    Returns:
        str: 图片说明.

    Raises:
        RuntimeError: 请求失败 响应非法或说明为空.
    """
    # 1. 读取图片并转 base64 数据 URI
    image_mime_type: str = guess_type(image_name)[0] or "application/octet-stream"
    image_base64: str = base64.b64encode(image_path_po.read_bytes()).decode("utf-8")
    image_data_uri: str = f"data:{image_mime_type};base64,{image_base64}"

    # 2. 组装请求地址 请求头 请求体
    request_url: str = f"{infra_config.llm.base_url.rstrip('/')}{_VISION_CHAT_PATH}"
    request_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {infra_config.llm.api_key}",
    }
    request_payload: dict[str, Any] = {
        "model": infra_config.llm.vl_model,
        "temperature": infra_config.llm.llm_temperature or _VISION_TEMPERATURE,
        # 千问系列私有参数: 关闭思考链, 与旧客户端保持一致
        "enable_thinking": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": image_prompt},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            }
        ],
    }

    # 3. 发送 POST 并校验 HTTP 状态码
    try:
        resp: requests.Response = requests.post(
            url=request_url,
            headers=request_headers,
            json=request_payload,
            timeout=_VISION_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"图片说明请求异常 | image={image_name} | error={exc}") from exc
    if resp.status_code != HTTP_STATUS_OK:
        raise RuntimeError(
            f"图片说明接口 HTTP 异常 | image={image_name} | status_code={resp.status_code}"
        )

    # 4. 解析响应并校验说明非空
    try:
        resp_json: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"图片说明响应不是 JSON | image={image_name}") from exc

    choice_list: list[Any] = resp_json.get("choices") or []
    if not choice_list:
        raise RuntimeError(f"图片说明响应缺少 choices | image={image_name}")
    message: dict[str, Any] = choice_list[0].get("message") or {}
    image_desc = message.get("content")
    if not isinstance(image_desc, str) or not image_desc.strip():
        raise RuntimeError(f"图片说明为空 | image={image_name}")
    return image_desc.strip()


# ---------------------------------------------------------------------------
# MinIO 上传
# ---------------------------------------------------------------------------
@function_log(func_name="上传图片到 MinIO", return_names=["image_url_map"])
def upload_images_to_minio(
    state: ImportGraphState,
    image_ref_list: list[ImageRef],
    doc_stem: str,
) -> dict[str, str]:
    """
    上传图片, 全部成功后清理过期对象.

    先上传后清理: 部分失败时旧图仍在, 原 Markdown 不会出现失效地址.

    业务逻辑:
        1. 列出该文档已有的图片对象, MinIO 不可用时返回空映射
        2. 逐张上传并生成访问 URL
        3. 部分失败则跳过清理, 返回已成功的映射
        4. 全部成功则删除本次未引用的过期对象
        5. 返回图片名到访问 URL 的映射

    Args:
        state: 图全局状态.
        image_ref_list: 图片引用.
        doc_stem: 文档文件名, 不含后缀, 作为对象前缀.

    Returns:
        dict[str, str]: 图片名到访问 URL 的映射.
    """
    # 1. 列出该文档已有的图片对象, 得到 文件名 -> 对象键
    task_id: str = str(state.get("task_id", ""))
    image_url_map: dict[str, str] = {}
    doc_image_prefix: str = minio_gateway.prefix_for(doc_stem)
    try:
        minio_client = minio_gateway.client
        stored_object_map: dict[str, str] = {
            Path(stored_object.object_name).name: stored_object.object_name
            for stored_object in minio_client.list_objects(
                bucket_name=minio_gateway.bucket_name,
                prefix=doc_image_prefix,
                recursive=True,
            )
        }
    except Exception as exc:
        # MinIO 不可用不影响文档导入, 保留原正文中的本地图片地址
        logger.warning(
            f"[警告] task_id={task_id} | MinIO 连接或列表失败, 跳过图片上传 | error={exc}"
        )
        return {}

    # 2. 逐张上传并生成访问 URL
    for image_name, image_path_po, _ in image_ref_list:
        image_mime_type: str = guess_type(image_name)[0] or "application/octet-stream"
        try:
            minio_client.fput_object(
                bucket_name=minio_gateway.bucket_name,
                object_name=minio_gateway.object_name(doc_stem, image_name),
                file_path=str(image_path_po),
                content_type=image_mime_type,
            )
        except Exception as exc:
            # 单张失败只记录, 不影响其他图片
            logger.warning(
                f"[警告] task_id={task_id} | 图片上传失败 "
                f"| image={image_name} | error={exc}"
            )
            continue
        image_url_map[image_name] = minio_gateway.build_image_url(doc_stem, image_name)
        logger.debug(f"[调试] task_id={task_id} | 图片上传完成 | image={image_name}")

    # 3. 部分失败则跳过清理, 返回已成功的映射
    if len(image_url_map) != len(image_ref_list):
        logger.warning(
            f"[警告] task_id={task_id} | 部分图片上传失败, 跳过过期对象清理 "
            f"| uploaded={len(image_url_map)} | total={len(image_ref_list)}"
        )
        return image_url_map

    # 4. 全部成功则删除本次未引用的过期对象
    outdated_object_list: list[str] = [
        object_name
        for image_name, object_name in stored_object_map.items()
        if image_name not in image_url_map
    ]
    removed_count: int = 0
    for object_name in outdated_object_list:
        try:
            minio_client.remove_object(
                bucket_name=minio_gateway.bucket_name,
                object_name=object_name,
            )
            removed_count += 1
        except Exception as exc:
            logger.warning(
                f"[警告] task_id={task_id} | 过期图片删除失败 "
                f"| object={object_name} | error={exc}"
            )
    if outdated_object_list:
        logger.info(
            f"[提示] task_id={task_id} | 过期图片清理完成 "
            f"| removed={removed_count} | failed={len(outdated_object_list) - removed_count}"
        )

    # 5. 返回图片名到访问 URL 的映射
    logger.info(f"[提示] task_id={task_id} | 图片上传完成 | count={len(image_url_map)}")
    return image_url_map


# ---------------------------------------------------------------------------
# 正文替换与落盘
# ---------------------------------------------------------------------------
@function_log(func_name="替换 Markdown 图片地址", return_names=["md_content"])
def replace_image_refs(
    md_content: str,
    image_url_map: dict[str, str],
    image_desc_map: dict[str, str],
) -> str:
    """
    把图片引用替换为 MinIO URL 与图片说明.

    业务逻辑:
        1. 遍历上传成功的图片
        2. 取说明, 缺失时用文件名
        3. 清洗说明并替换原引用
        4. 返回替换后的正文

    Args:
        md_content: 原正文.
        image_url_map: 图片名到 URL.
        image_desc_map: 图片名到说明.

    Returns:
        str: 替换后的正文.
    """
    # 1. 遍历上传成功的图片
    for image_name, image_url in image_url_map.items():
        # 2. 取说明, 缺失时用文件名
        image_desc: str = image_desc_map.get(image_name) or image_name

        # 3. 清洗说明并替换原引用:
        #    说明里的换行会破坏 Markdown, 方括号会截断替代文本
        image_desc = " ".join(image_desc.split())
        image_desc = image_desc.replace("[", "【").replace("]", "】")
        if not image_desc:
            image_desc = image_name
        replacement: str = f"![{image_desc}]({image_url})"
        image_ref_pattern: str = _build_image_ref_pattern(image_name)
        # 用函数替换, 避免说明或 URL 里的反斜杠被当作正则分组引用
        md_content = re.sub(image_ref_pattern, lambda _match: replacement, md_content)

    # 4. 返回替换后的正文
    return md_content


@function_log(func_name="保存增强后的 Markdown", return_names=["enriched_md_path"])
def save_enriched_md(enriched_md_content: str, md_path_po: Path) -> str:
    """
    保存增强后的 Markdown 副本, 不覆盖原文件.

    业务逻辑:
        1. 生成 _new.md 路径
        2. 写入正文
        3. 返回路径字符串

    副作用:
        写入 {原文件名}_new.md.

    Args:
        enriched_md_content: 增强后的正文.
        md_path_po: 原 md 路径.

    Returns:
        str: 新 md 路径.
    """
    # 1. 生成 _new.md 路径
    enriched_md_path_po: Path = md_path_po.with_name(
        f"{md_path_po.stem}_new{md_path_po.suffix}"
    )

    # 2. 写入正文
    enriched_md_path_po.write_text(enriched_md_content, encoding="utf-8")

    # 3. 返回路径字符串
    return str(enriched_md_path_po)
