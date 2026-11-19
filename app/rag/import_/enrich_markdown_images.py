"""
Markdown 图片增强服务模块。

纯函数服务，负责扫描 Markdown 中的图片引用，调用多模态模型生成图片说明，
上传至 MinIO 对象存储，并替换 Markdown 中的图片地址。
"""
from app.constants.prompt_constants import PROMPT_IMAGE_SUMMARY
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.logger import logger, function_log
from app.shared.runtime.load_prompt import load_prompt
from app.infra.llm.providers import llm_provider
from app.constants.mineru_constants import *
from app.constants.file_constants import *
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from mimetypes import guess_type
from pathlib import Path
import base64
import re


def enrich_markdown_images(state: ImportGraphState) -> ImportGraphState:
    """
    Markdown 图片增强服务。

    执行步骤：
        1. 扫描 Markdown 中的图片。
        2. 调用多模态生成图片说明。
        3. 上传图片到 MinIO。
        4. 替换 Markdown 图片地址并回写 md_path。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state


@function_log(
    func_name="调用多模态生成图片意图",
    return_names=["images_info_detail"]
)
def summary_image_info(state: ImportGraphState, images_info_list: list[tuple[str, Path, tuple[str, str]]],
                       md_file_name: str) -> dict[str, str]:
    """
    核心功能：调用多模态视觉模型为 Markdown 中的图片生成文字意图

    业务逻辑：
        1. 初始化多模态视觉大模型客户端
        2. 遍历待处理的图片信息列表
        3. 构建图片说明 Prompt 模板
        4. 推断图片 MIME 类型，并读取文件转换为 base64 编码
        5. 组装多模态消息(HumanMessage)并构建调用链
        6. 调用大模型生成说明，并记录到字典中

    Args:
        (state)流程全局状态
        (images_info_list)提取到的图片名、路径及上下文列表
        (md_file_name)当前处理的 Markdown 文件名

    Returns:
        dict[str, str]: 图片名与模型生成的文字说明字典

    Raises:
        RuntimeError: 当图片读取失败或大模型调用失败时抛出
    """
    # 1.
    task_id: str = state.get("task_id", "") or ""
    images_info_detail: dict[str, str] = {}
    vision_model_chat = llm_provider.vision_chat()

    # 2. 遍历列表处理每一张图片
    for image_name, image_path_po, image_context in images_info_list:
        # 3. 使用提示词模板构建 Prompt
        image_describe: str = load_prompt(PROMPT_IMAGE_SUMMARY, file_name=md_file_name, image_context=image_context)

        # 4. 取图片类型并转换 base64格式
        image_type: str = guess_type(image_name)[0]
        image_base64: str = base64.b64encode(image_path_po.read_bytes()).decode("utf-8")

        # 5. 组装多模态消息
        message = HumanMessage(
            content=[
                {"type": "text", "text": image_describe},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_type};base64,{image_base64}"},
                },
            ]
        )

        # 6. 构建调用链并执行
        lang_chains = vision_model_chat | StrOutputParser()
        image_info: str = lang_chains.invoke([message])
        images_info_detail[image_name] = image_info

        logger.debug(f"task_id({task_id})【调试信息】-|-生成图片意图成功 image_name({image_name})")

    logger.info(f"task_id({task_id})【业务提示】-|-全部图片说明生成完毕,共生成({len(images_info_detail)})条")
    return images_info_detail


@function_log(
    func_name="扫描 Markdown 中的图片及上下文",
    return_names=["images_info_list"]
)
def scan_images_info(state: ImportGraphState, md_images_dir_path_po: Path, md_content: str) -> list[
    tuple[str, Path, tuple[str, str]]]:
    """
    核心功能：扫描图片目录，匹配 Markdown 中的图片引用，并提取上下文

    业务逻辑：
        1. 遍历图片目录下的所有文件(md_images_dir_path_po.iterdir)
        2. 过滤掉非图片后缀的文件
        3. 使用正则到 md_content 中匹配该图片的引用
        4. 匹配成功后，截取图片引用的上文和下文
        5. 将 (图片名, 图片Path对象, (上文, 下文)) 组装成元组并添加到列表
        6. 返回提取到的数据列表

    Args:
        (state)流程全局状态
        (md_images_dir_path_po)图片所在的目录 Path 对象
        (md_content)Markdown 文本内容

    Returns:
        list[tuple[str, Path, tuple[str, str]]]: 包含图片名、图片路径对象及上下文字符串元组的列表
    """
    # 1. 获取目录下所有文件
    task_id: str = state.get("task_id", "") or ""
    md_images_generator = md_images_dir_path_po.iterdir()
    images_info_list: list[tuple[str, Path, tuple[str, str]]] = []

    # 2. 循环每一张图片对象
    for md_image_path_po in md_images_generator:
        # 过滤文件夹
        if not md_image_path_po.is_file():
            continue

        # 过滤不支持的后缀
        if md_image_path_po.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            logger.debug(f"task_id({task_id})【调试信息】-|-跳过不支持的文件类型 md_image_path_po({md_image_path_po})")
            continue

        md_image_name: str = md_image_path_po.name

        # 3. 定义 Markdown 图片匹配正则规则
        # 匹配格式：![任意文字](任意路径/图片名 任意参数)
        match = re.search(r"\!\[.*?\]\(.*?" + re.escape(md_image_name) + ".*?\)", md_content)

        # 检查是否匹配
        if not match:
            logger.debug(f"task_id({task_id})【调试】-|-Markdown 中未找到该图片的引用 md_image_name({md_image_name})")
            continue

        # 4. 获取图片上下文
        left_index = match.start()
        right_index = match.end()
        left_index_context: str = md_content[max(left_index - IMAGE_CONTEXT_CHAR_LENGTH, 0): left_index].strip()
        right_index_context: str = md_content[
            right_index: min(right_index + IMAGE_CONTEXT_CHAR_LENGTH, len(md_content))].strip()

        # 5. 将(图片名, 图片Path对象, (上文, 下文))组装成元组并添加到列表
        images_info_list.append((md_image_name, md_image_path_po, (left_index_context, right_index_context)))

    logger.info(f"task_id({task_id})【业务提示】-|-图片扫描完成,共提取到有效图片信息({len(images_info_list)})条")
    return images_info_list


@function_log(
    func_name="校验并读取 Markdown 数据",
    return_names=["md_content", "md_path_po", "md_images_dir_path_po"]
)
def validates_and_get_data(state: ImportGraphState) -> tuple[str, Path, Path]:
    """
    核心功能：校验 Markdown 路径并读取内容，获取图片目录

    业务逻辑：
       1. 从(state)中获取 md_path 与 md_content
       2. 判断(md_path)类型及是否为空
       3. 类型转换(md_path: str->md_path_po: Path)，并判断是否为常规文件
       4. 读取文件内容写入 md_content，并回写 state
       5. 拼接并判断图片所在目录(images_md_dir_path_po)是否存在

    Args:
       (state)流程全局状态

    Returns:
       tuple[(md_content)md文本内容, (md_path_po)md文件路径, (images_md_dir_path_po)图片所在目录]

    Raises:
       ValueError: 当 md_path 缺失或非字符串时抛出
       FileNotFoundError: 当 md 文件或图片目录不存在时抛出
       RuntimeError: 当读取 md 文件失败时抛出
    """
    # 1. 从(state)中获取 md_path 与 md_content
    task_id: str = state.get("task_id", "") or ""
    md_path: str = state.get("md_path", "")

    # 2. 判断(md_path)是否为空
    if not md_path.strip():
        logger.error(f"task_id({task_id})【业务终止】-|-Markdown文件路径非法 md_path({md_path})")
        raise ValueError(f"task_id({task_id})【业务终止】-|-Markdown文件路径非法 md_path({md_path})")

    # 3. 类型转换并判断是否为常规文件
    md_path_po: Path = Path(md_path)
    if not md_path_po.is_file():
        logger.error(f"task_id({task_id})【业务终止】-|-Markdown文件不存在或不是常规文件 md_path_po({md_path_po})")
        raise FileNotFoundError(
            f"task_id({task_id})【业务终止】-|-Markdown文件不存在或不是常规文件 md_path_po({md_path_po})")

    # 4. 读取文件内容并回写 state
    md_content: str = md_path_po.read_text(encoding="utf-8")
    state["md_content"] = md_content

    # 5. 拼接路径并判断图片目录是否存在
    md_images_dir_path_po: Path = md_path_po.parent / MINERU_OUTPUT_ZIP_IMAGES_DIR

    if not md_images_dir_path_po.is_dir():
        logger.error(
            f"task_id({task_id})【业务终止】-|-Markdown关联的图片目录不存在 md_images_dir_path_po({md_images_dir_path_po})")
        raise FileNotFoundError(
            f"task_id({task_id})【业务终止】-|-Markdown关联的图片目录不存在 md_images_dir_path_po({md_images_dir_path_po})")

    return md_content, md_path_po, md_images_dir_path_po
