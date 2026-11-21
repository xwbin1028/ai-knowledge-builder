"""
文档切分服务.

职责: 按标题粗切, 超长细切, 短碎片合并, 补齐元数据并备份.
边界: 不负责 PDF 解析 向量化与入库, 只处理 state 中的 Markdown 正文.
"""
import json
import re
from pathlib import Path
from typing import Any, Final

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.constants.split_constants import (
    CHUNK_MAX_SIZE,
    CHUNK_MIN,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNKS_JSON_SUFFIX,
    CODE_FENCE_MARKERS,
    PREAMBLE_TITLE,
    SPLIT_SEPARATORS,
    TITLE_PATTERN,
)
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import function_log, logger

# 切片字典, 键随流程逐步补齐: title content parent_title part file_title
Chunk = dict[str, Any]

# 标题行正则, 只对代码块外的行生效
_TITLE_RE: Final[re.Pattern[str]] = re.compile(TITLE_PATTERN)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="按标题与长度切分文档", return_names=["state"])
def split_document(state: ImportGraphState) -> ImportGraphState:
    """
    切分文档主入口.

    业务逻辑:
        1. 校验并读取 Markdown, 得到正文 标题 路径
        2. 按标题粗切, 得到 title_chunks
        3. 超长切片细切
        4. 短碎片合并
        5. 补齐元数据并备份
        6. 回写 state["chunks"]

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 chunks 的状态.

    Raises:
        ValueError: md_path 或正文为空.
        FileNotFoundError: md 文件不存在.
    """
    task_id: str = str(state.get("task_id", ""))

    # 1. 校验并读取 Markdown, 得到正文 标题 路径
    md_content, file_title, md_path_po = read_markdown(state)

    # 2. 按标题粗切, 得到 title_chunks
    title_chunks: list[Chunk] = split_by_title(md_content, task_id)

    # 3. 超长切片细切
    size_chunks: list[Chunk] = split_long_chunks(title_chunks, task_id)

    # 4. 短碎片合并
    merged_chunks: list[Chunk] = merge_short_chunks(size_chunks, task_id)

    # 5. 补齐元数据并备份
    append_chunk_metadata(merged_chunks, file_title)
    backup_chunks(merged_chunks, md_path_po, task_id)

    # 6. 回写 state["chunks"]
    state["chunks"] = merged_chunks
    return state


# ---------------------------------------------------------------------------
# 读取与校验
# ---------------------------------------------------------------------------
@function_log(
    func_name="校验并读取 Markdown",
    return_names=["md_content", "file_title", "md_path_po"],
)
def read_markdown(state: ImportGraphState) -> tuple[str, str, Path]:
    """
    校验并读取 Markdown.

    业务逻辑:
        1. 取 task_id md_path file_title md_content
        2. 校验 md_path 并转 Path
        3. 正文为空则读文件, 仍为空则终止
        4. 标题为空则用文件主名
        5. 统一换行并回写 state

    副作用:
        回写 state["md_content"] 与 state["file_title"].

    Args:
        state: 图全局状态.

    Returns:
        tuple[str, str, Path]: 正文, 标题, md 文件.

    Raises:
        ValueError: md_path 或正文为空, 或文件不是 UTF-8.
        FileNotFoundError: md 文件不存在.
    """
    # 1. 取 task_id md_path file_title md_content
    task_id: str = str(state.get("task_id", ""))
    md_path: str = str(state.get("md_path") or "")
    file_title: str = str(state.get("file_title") or "").strip()
    md_content: str = str(state.get("md_content") or "")

    # 2. 校验 md_path 并转 Path
    if not md_path.strip():
        raise business_error(ValueError, task_id, "Markdown 路径为空", md_path=md_path)
    md_path_po: Path = Path(md_path)
    if not md_path_po.is_file():
        raise business_error(FileNotFoundError, task_id, "Markdown 文件不存在", md_path=md_path_po)

    # 3. 正文为空则读文件, 仍为空则终止
    if not md_content.strip():
        try:
            md_content = md_path_po.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise business_error(
                ValueError, task_id, "Markdown 不是 UTF-8 编码", md_path=md_path_po
            ) from exc
        if not md_content.strip():
            raise business_error(ValueError, task_id, "Markdown 正文为空", md_path=md_path_po)

    # 4. 标题为空则用文件主名
    if not file_title:
        file_title = md_path_po.stem
        logger.warning(f"[警告] task_id={task_id} | 标题为空, 用文件主名 | file_title={file_title}")

    # 5. 统一换行并回写 state
    md_content = md_content.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    state["md_content"] = md_content
    state["file_title"] = file_title
    return md_content, file_title, md_path_po


# ---------------------------------------------------------------------------
# 标题切分
# ---------------------------------------------------------------------------
@function_log(func_name="按标题粗切 Markdown", return_names=["title_chunks"])
def split_by_title(md_content: str, task_id: str) -> list[Chunk]:
    """
    按 Markdown 标题粗切.

    业务逻辑:
        1. 准备收集容器与代码块标记
        2. 逐行扫描, 保留缩进并识别代码块围栏
        3. 遇到标题结算上一节, 开头无标题的内容归入前言
        4. 普通行原样追加到当前节
        5. 扫描结束结算最后一节

    Args:
        md_content: Markdown 正文.
        task_id: 任务 ID, 只用于日志.

    Returns:
        list[Chunk]: 标题切片, 每片含 title 与 content.
    """
    # 1. 准备收集容器与代码块标记
    title_chunks: list[Chunk] = []
    current_title: str = ""
    current_lines: list[str] = []
    is_code_block: bool = False
    fence_marker: str = ""

    # 2. 逐行扫描, 保留缩进并识别代码块围栏
    for raw_line in md_content.split("\n"):
        line: str = raw_line.rstrip()
        stripped_line: str = line.strip()

        if not is_code_block and not stripped_line and not current_lines:
            # 文档开头的空行忽略, 避免前言切片以空行开头
            continue

        if stripped_line.startswith(CODE_FENCE_MARKERS):
            if not is_code_block:
                is_code_block = True
                fence_marker = "```" if stripped_line.startswith("```") else "~~~"
            elif stripped_line.startswith(fence_marker):
                is_code_block = False
            current_lines.append(line)
            continue

        # 3. 遇到标题结算上一节, 开头无标题的内容归入前言
        if not is_code_block and _TITLE_RE.match(stripped_line):
            if current_title:
                _flush_chunk(title_chunks, current_title, current_lines, True)
            else:
                _flush_chunk(title_chunks, PREAMBLE_TITLE, current_lines, False)
            current_title = stripped_line
            current_lines = [stripped_line]
            continue

        # 4. 普通行原样追加到当前节
        current_lines.append(line)

    # 5. 扫描结束结算最后一节
    if current_title:
        _flush_chunk(title_chunks, current_title, current_lines, True)
    else:
        _flush_chunk(title_chunks, PREAMBLE_TITLE, current_lines, False)

    logger.info(f"[提示] task_id={task_id} | 标题粗切完成 | chunks={len(title_chunks)}")
    return title_chunks


def _flush_chunk(chunks: list[Chunk], title: str, lines: list[str], is_heading: bool) -> None:
    """结算当前累计行, 去掉首尾空行, 丢弃只有标题没有正文的切片."""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return
    if is_heading and len(lines) <= 1:
        return
    chunks.append({"title": title, "content": "\n".join(lines)})


@function_log(func_name="细切超长切片", return_names=["size_chunks"])
def split_long_chunks(title_chunks: list[Chunk], task_id: str) -> list[Chunk]:
    """
    细切超长切片.

    业务逻辑:
        1. 准备结果列表
        2. 遍历粗切结果, 超过 CHUNK_SIZE 的交给递归切割器
        3. 返回细切后的切片

    Args:
        title_chunks: 按标题粗切得到的切片.
        task_id: 任务 ID, 只用于日志.

    Returns:
        list[Chunk]: 长度受控的切片.
    """
    # 1. 准备结果列表
    size_chunks: list[Chunk] = []

    # 2. 遍历粗切结果, 超过 CHUNK_SIZE 的交给递归切割器
    for chunk in title_chunks:
        if len(chunk["content"]) > CHUNK_SIZE:
            size_chunks.extend(_split_one_chunk(chunk))
            continue
        size_chunks.append(chunk)

    # 3. 返回细切后的切片
    logger.info(f"[提示] task_id={task_id} | 超长切片细切完成 | chunks={len(size_chunks)}")
    return size_chunks


def _split_one_chunk(chunk: Chunk) -> list[Chunk]:
    """
    用递归切割器细切单个超长切片.

    业务逻辑:
        1. 取标题与正文
        2. 去掉正文首行的标题, 得到待切正文
        3. 计算可用长度与重叠长度
        4. 逐片组装子切片, 重复写入标题作为上下文

    Args:
        chunk: 单个超长切片.

    Returns:
        list[Chunk]: 子切片, 标题带 _1 _2 后缀; 无法细切时返回原切片.
    """
    # 1. 取标题与正文
    title: str = chunk["title"]
    content: str = chunk["content"]

    # 2. 去掉正文首行的标题, 得到待切正文
    body: str = _strip_title_line(content, title)
    if not body.strip():
        return [chunk]

    # 3. 计算可用长度与重叠长度
    title_prefix: str = f"{title}\n"
    if len(title_prefix) >= CHUNK_SIZE:
        # 标题过长时不再写进每片正文, 避免正文被标题占满
        title_prefix = ""
    chunk_size: int = max(CHUNK_SIZE - len(title_prefix), 1)
    chunk_overlap: int = min(CHUNK_OVERLAP, chunk_size // 2)
    text_splitter = RecursiveCharacterTextSplitter(
        separators=list(SPLIT_SEPARATORS),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # 4. 逐片组装子切片, 重复写入标题作为上下文
    part_texts: list[str] = text_splitter.split_text(body)
    if len(part_texts) <= 1:
        return [chunk]

    sub_chunks: list[Chunk] = []
    for part_index, part_text in enumerate(part_texts, start=1):
        sub_chunks.append(
            {
                "parent_title": title,
                "title": f"{title}_{part_index}",
                "part": part_index,
                "content": f"{title_prefix}{part_text}" if title_prefix else part_text,
            }
        )
    return sub_chunks


def _strip_title_line(content: str, title: str) -> str:
    """去掉正文首行的标题, 首行不是标题时原样返回."""
    first_line, _, rest = content.partition("\n")
    if first_line.strip() == title.strip():
        return rest
    return content


# ---------------------------------------------------------------------------
# 合并与收尾
# ---------------------------------------------------------------------------
@function_log(func_name="合并短碎片切片", return_names=["merged_chunks"])
def merge_short_chunks(size_chunks: list[Chunk], task_id: str) -> list[Chunk]:
    """
    合并同一标题下的短碎片.

    合并条件: 当前片或下一片短于 CHUNK_MIN, 两片同 parent_title,
    且合并后不超过 CHUNK_MAX_SIZE.

    业务逻辑:
        1. 准备结果列表与 base 片
        2. 逐片判断能否并入 base, 能并则拼接正文
        3. 不能并则结算 base, 下一片成为新 base
        4. 结算最后一片并按顺序重排 part

    Args:
        size_chunks: 长度受控的切片.
        task_id: 任务 ID, 只用于日志.

    Returns:
        list[Chunk]: 合并后的切片.
    """
    # 1. 准备结果列表与 base 片
    merged_chunks: list[Chunk] = []
    base_chunk: Chunk | None = None

    # 2. 逐片判断能否并入 base, 能并则拼接正文
    for next_chunk in size_chunks:
        if base_chunk is None:
            base_chunk = dict(next_chunk)
            continue
        if _can_merge(base_chunk, next_chunk):
            base_chunk["content"] = f"{base_chunk['content']}\n{next_chunk['content']}"
            continue

        # 3. 不能并则结算 base, 下一片成为新 base
        merged_chunks.append(base_chunk)
        base_chunk = dict(next_chunk)

    # 4. 结算最后一片并按顺序重排 part
    if base_chunk is not None:
        merged_chunks.append(base_chunk)
    _renumber_parts(merged_chunks)
    logger.info(f"[提示] task_id={task_id} | 短碎片合并完成 | chunks={len(merged_chunks)}")
    return merged_chunks


def _can_merge(base_chunk: Chunk, next_chunk: Chunk) -> bool:
    """判断能否合并: 至少一片是短碎片, 同 parent_title, 合并后不超上限."""
    base_length: int = len(base_chunk["content"])
    next_length: int = len(next_chunk["content"])
    if base_length >= CHUNK_MIN and next_length >= CHUNK_MIN:
        return False

    parent_title: str = str(base_chunk.get("parent_title") or "")
    if not parent_title or parent_title != next_chunk.get("parent_title"):
        # parent_title 为空表示该片没有被细切, 不能跨标题合并
        return False

    return base_length + 1 + next_length <= CHUNK_MAX_SIZE


def _renumber_parts(chunks: list[Chunk]) -> None:
    """按出现顺序重排细切片的后缀与 part, 保持标题和序号一致."""
    part_counters: dict[str, int] = {}
    for chunk in chunks:
        parent_title: str = str(chunk.get("parent_title") or "")
        if not parent_title or chunk.get("title") == parent_title:
            continue
        part_counters[parent_title] = part_counters.get(parent_title, 0) + 1
        part_index: int = part_counters[parent_title]
        chunk["part"] = part_index
        chunk["title"] = f"{parent_title}_{part_index}"


def append_chunk_metadata(chunks: list[Chunk], file_title: str) -> None:
    """补齐 file_title parent_title part 三个元数据字段."""
    for chunk in chunks:
        chunk["file_title"] = file_title
        chunk.setdefault("part", 1)
        chunk.setdefault("parent_title", chunk["title"])


@function_log(func_name="备份切分结果")
def backup_chunks(chunks: list[Chunk], md_path_po: Path, task_id: str) -> None:
    """
    备份切分结果为 JSON, 备份失败只告警.

    业务逻辑:
        1. 拼出与 md 同目录的备份路径
        2. 写入 JSON 文本
        3. 写入失败时记录告警

    副作用:
        写入 {md_stem}_chunks.json.

    Args:
        chunks: 切分结果.
        md_path_po: 原 md 路径.
        task_id: 任务 ID, 只用于日志.
    """
    # 1. 拼出与 md 同目录的备份路径
    backup_path_po: Path = md_path_po.with_name(f"{md_path_po.stem}{CHUNKS_JSON_SUFFIX}")

    # 2. 写入 JSON 文本
    try:
        backup_path_po.write_text(
            json.dumps(chunks, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        # 3. 写入失败时记录告警, 备份不是主流程, 不中断导入
        logger.warning(
            f"[警告] task_id={task_id} | 切分备份写入失败, 跳过 "
            f"| path={backup_path_po} | error={exc}"
        )
        return

    logger.info(
        f"[提示] task_id={task_id} | 切分备份完成 "
        f"| path={backup_path_po} | chunks={len(chunks)}"
    )
