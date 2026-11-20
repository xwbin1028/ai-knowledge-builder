"""
Markdown 图片增强.

扫描图片引用, 调多模态模型生成说明, 上传 MinIO 并替换 Markdown 中的图片地址.
"""
import base64
import re
from mimetypes import guess_type
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from minio.deleteobjects import DeleteObject

from app.constants.file_constants import SUPPORTED_IMAGE_SUFFIXES
from app.constants.mineru_constants import IMAGE_CONTEXT_CHAR_LENGTH, MINERU_OUTPUT_ZIP_IMAGES_DIR
from app.constants.prompt_constants import PROMPT_IMAGE_SUMMARY
from app.infra.llm.providers import llm_provider
from app.infra.minio.minio_gateway import minio_gateway
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.load_prompt import load_prompt
from app.shared.runtime.logger import function_log, logger

# 图片引用: 图片名, 图片 Path, (上文, 下文)
ImageRef = tuple[str, Path, tuple[str, str]]

# 图片引用正则: ![任意说明](任意路径/图片名 任意参数)
_build_image_ref_pattern = lambda image_name: (
    r"\!\[.*?\]\(.*?" + re.escape(image_name) + ".*?\)"
)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def enrich_markdown_images(state: ImportGraphState) -> ImportGraphState:
    """
    Markdown 图片增强主入口.

    业务逻辑:
        1. 加载并校验 md, 定位图片目录
        2. 图片目录缺失或为空则跳过
        3. 收集图片引用, 无引用则跳过
        4. 调多模态生成图片说明
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
    task_id: str = state.get("task_id", "")

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

    # 4. 调多模态生成图片说明
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
        f"[提示] task_id={task_id} | 图片增强完成 | count={len(image_url_map)} | md_path={enriched_md_path}"
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
    task_id: str = state.get("task_id", "")
    md_path: str = state.get("md_path", "")
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
    task_id: str = state.get("task_id", "")
    image_ref_list: list[ImageRef] = []

    for image_path_po in image_dir_po.iterdir():
        # 2. 过滤非文件与不支持的后缀
        if not image_path_po.is_file():
            continue
        if image_path_po.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            logger.debug(f"[调试] task_id={task_id} | 跳过不支持的后缀 | file={image_path_po}")
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
@function_log(func_name="调用多模态生成图片说明", return_names=["image_desc_map"])
def describe_images(
    state: ImportGraphState,
    image_ref_list: list[ImageRef],
    doc_stem: str,
) -> dict[str, str]:
    """
    调用视觉模型为图片生成文字说明.

    业务逻辑:
        1. 初始化视觉客户端与结果字典
        2. 遍历图片引用
        3. 渲染图片说明 prompt
        4. 读取图片并转 base64
        5. 组装多模态消息与调用链
        6. 调用模型并把说明写入字典

    Args:
        state: 图全局状态.
        image_ref_list: 收集到的图片引用.
        doc_stem: 当前 Markdown 文件名, 不含后缀.

    Returns:
        dict[str, str]: 图片名到说明的映射.

    Raises:
        RuntimeError: 图片读取或模型调用失败.
    """
    # 1. 初始化视觉客户端与结果字典
    task_id: str = state.get("task_id", "")
    image_desc_map: dict[str, str] = {}
    vision_client = llm_provider.vision_chat()

    # 2. 遍历图片引用
    for image_name, image_path_po, image_context in image_ref_list:
        # 3. 渲染图片说明 prompt
        image_prompt: str = load_prompt(
            PROMPT_IMAGE_SUMMARY,
            file_name=doc_stem,
            image_context=image_context,
        )

        # 4. 读取图片并转 base64
        image_mime_type: str = guess_type(image_name)[0] or "application/octet-stream"
        image_base64: str = base64.b64encode(image_path_po.read_bytes()).decode("utf-8")

        # 5. 组装多模态消息与调用链
        message = HumanMessage(
            content=[
                {"type": "text", "text": image_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"},
                },
            ]
        )
        vision_chain = vision_client | StrOutputParser()

        # 6. 调用模型并把说明写入字典
        image_desc_map[image_name] = vision_chain.invoke([message])
        logger.debug(f"[调试] task_id={task_id} | 图片说明生成 | image={image_name}")

    logger.info(f"[提示] task_id={task_id} | 图片说明全部生成 | count={len(image_desc_map)}")
    return image_desc_map


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

    设计说明:
        先上传, 全部成功后才清理旧对象. 部分图片失败时旧图仍在,
        原 Markdown 不会出现图片地址失效.

    业务逻辑:
        1. 列出当前文档在 MinIO 中已有的图片对象
        2. 逐张上传本次解析出的图片，并生成访问 URL
        3. 检查是否全部上传成功，若部分失败则放弃清理过期对象
        4. 若全部成功，对比历史对象，删除不在本次集合中的过期对象
        5. 返回图片名到访问 URL 的映射

    Args:
        state: 图全局状态.
        image_ref_list: 图片引用.
        doc_stem: 文档文件名, 不含后缀, 作为对象前缀.

    Returns:
        dict[str, str]: 图片名到访问 URL 的映射.
    """
    # 1. 列出该文档已有的图片对象
    # 1.1 task_id 只用于日志; image_url_map 收集本次上传成功的图片名与 URL
    task_id: str = state.get("task_id", "")
    image_url_map: dict[str, str] = {}

    # 1.2 首次访问 client 会懒加载 MinIO 客户端, 并确保桶存在
    minio_client = minio_gateway.client

    # 1.3 前缀由 gateway 统一拼成 图片前缀/文档名/, 末尾带 /, 避免匹配到同名前缀的其他文档
    doc_image_prefix: str = minio_gateway.prefix_for(doc_stem)

    # 1.4 list_objects 返回生成器, 这里 list() 一次取出:
    #     后面要判空 统计数量, 并与本次上传结果逐个比对
    stored_object_list: list = list(
        minio_client.list_objects(
            bucket_name=minio_gateway.bucket_name,
            prefix=doc_image_prefix,
            recursive=True,
        )
    )

    # 2. 逐张上传并生成访问 URL
    # 2.1 ImageRef 结构为 (图片名, 本地 Path, (上文, 下文)), 上传只用前两项
    for image_name, image_path_po, _ in image_ref_list:
        # 2.2 guess_type 可能返回 None, 兜底 application/octet-stream, 避免空 Content-Type
        image_mime_type: str = guess_type(image_name)[0] or "application/octet-stream"
        try:
            # 2.3 object_name 同样由 gateway 拼接, 保证与第 1 步的列表前缀规则一致
            minio_client.fput_object(
                bucket_name=minio_gateway.bucket_name,
                object_name=minio_gateway.object_name(doc_stem, image_name),
                file_path=str(image_path_po),
                content_type=image_mime_type,
            )
        except Exception:
            # 2.4 单张失败只记录并跳过, 不影响其他图片; 失败会在第 3 步按数量发现
            logger.exception(f"[异常] task_id={task_id} | 图片上传失败 | image={image_name}")
            continue

        # 2.5 只有成功才写入 map, 它是第 3 步判断是否全部成功的依据
        image_url_map[image_name] = minio_gateway.build_image_url(doc_stem, image_name)
        logger.debug(f"[调试] task_id={task_id} | 图片上传完成 | image={image_name}")

    # 3. 全部成功后删除不在本次集合的过期对象
    # 3.1 成功数少于引用数, 说明至少有一张失败
    if len(image_url_map) != len(image_ref_list):
        # 3.2 此时 Markdown 还没替换, 旧图可能仍被引用; 直接返回已成功的部分
        logger.warning(f"[警告] task_id={task_id} | 部分图片上传失败, 跳过过期对象清理")
        return image_url_map

    # 4. 全部成功, 对比历史对象并删除过期对象
    # 4.1 对象键形如 图片前缀/文档名/图片名, 取最后一段文件名与本次结果比对
    outdated_object_list: list = [
        stored_object for stored_object in stored_object_list
        if Path(stored_object.object_name).name not in image_url_map
    ]

    # 4.2 没有过期对象就不调用删除接口, 省一次请求
    if outdated_object_list:
        # 4.3 删除接口要 DeleteObject 列表, 不是字符串列表
        delete_object_list = [DeleteObject(item.object_name) for item in outdated_object_list]

        # 4.4 remove_objects 返回生成器, list() 才会真正发请求并收集每个对象的错误
        delete_error_list: list = list(
            minio_client.remove_objects(
                bucket_name=minio_gateway.bucket_name,
                delete_object_list=delete_object_list,
            )
        )

        # 4.5 删除失败不影响新图, 按对象记录 code, 方便排查权限或对象锁问题
        for delete_error in delete_error_list:
            logger.warning(
                f"[警告] task_id={task_id} | 过期图片删除失败 "
                f"| object={delete_error.name} | code={delete_error.code}"
            )
        logger.info(
            f"[提示] task_id={task_id} | 过期图片清理完成 | count={len(outdated_object_list)}"
        )

    # 5. 返回图片名到 URL 的映射
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
        2. 用说明与 URL 替换原引用
        3. 返回替换后的正文

    Args:
        md_content: 原正文.
        image_url_map: 图片名到 URL.
        image_desc_map: 图片名到说明.

    Returns:
        str: 替换后的正文.
    """
    # 1. 遍历上传成功的图片
    for image_name, image_url in image_url_map.items():
        image_desc: str = image_desc_map.get(image_name) or image_name

        # 2. 用说明与 URL 替换原引用, lambda 避免反斜杠被当作分组引用
        image_ref_pattern: str = _build_image_ref_pattern(image_name)
        md_content = re.sub(
            image_ref_pattern, lambda _: f"![{image_desc}]({image_url})", md_content
        )

    # 3. 返回替换后的正文
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
        写入新 md 文件.

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
