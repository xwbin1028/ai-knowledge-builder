"""
主体名称识别服务.

职责: 用 chunks 识别 item_name, 生成稠密与稀疏向量并写入 Milvus.
边界: 不负责切分与切片向量化, 只维护 item_name 集合与 state 回填.
"""
import json
from pathlib import Path
from typing import Any

from pymilvus import DataType, MilvusClient

from app.constants.item_name_constants import (
    DEFAULT_FILE_TITLE,
    ITEM_NAME_DENSE_INDEX_NAME,
    ITEM_NAME_DENSE_INDEX_TYPE,
    ITEM_NAME_DENSE_METRIC_TYPE,
    ITEM_NAME_FIELD_DENSE_VECTOR,
    ITEM_NAME_FIELD_FILE_TITLE,
    ITEM_NAME_FIELD_ITEM_NAME,
    ITEM_NAME_FIELD_PK,
    ITEM_NAME_FIELD_SPARSE_VECTOR,
    ITEM_NAME_HNSW_EF_CONSTRUCTION,
    ITEM_NAME_HNSW_M,
    ITEM_NAME_RECOGNITION_CHUNKS_TOP_K,
    ITEM_NAME_SPARSE_INDEX_NAME,
    ITEM_NAME_SPARSE_INDEX_TYPE,
    ITEM_NAME_SPARSE_INVERTED_ALGO,
    ITEM_NAME_SPARSE_METRIC_TYPE,
    ITEM_NAME_TEXT_MAX_LENGTH,
    ITEM_NAME_VECTOR_DIM,
)
from app.constants.prompt_constants import PROMPT_ITEM_NAME_RECOGNITION
from app.constants.split_constants import CHUNKS_JSON_SUFFIX, LEGACY_CHUNKS_JSON_NAME
from app.infra.llm.providers import llm_provider
from app.infra.vectorstore.milvus_gateway import milvus_gateway
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.load_prompt import load_prompt
from app.shared.runtime.logger import function_log, logger

# 切片字典, 与 split_document 的输出保持一致
Chunk = dict[str, Any]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="识别主体名称并写入索引", return_names=["state"])
def recognize_and_index_item_name(state: ImportGraphState) -> ImportGraphState:
    """
    识别主体名称并写入索引.

    业务逻辑:
        1. 读取并校验 chunks 与 file_title
        2. 调模型识别 item_name
        3. 生成稠密与稀疏向量
        4. 确保 item_name 集合可用
        5. 按 file_title 覆盖旧记录
        6. 回填 chunks 与 state
        7. 返回 state

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 item_name 与 chunks 的状态.

    Raises:
        ValueError: chunks 与备份都为空, 或 BGE-M3 模型未配置.
        RuntimeError: 模型调用 向量生成或 Milvus 操作失败.
    """
    task_id: str = str(state.get("task_id", ""))

    # 1. 读取并校验 chunks 与 file_title
    file_title, chunks = load_item_name_input(state)

    # 2. 调模型识别 item_name
    item_name: str = recognize_item_name(chunks, file_title, task_id)

    # 3. 生成稠密与稀疏向量
    dense_vector, sparse_vector = embed_item_name(item_name, task_id)

    # 4. 确保 item_name 集合可用
    ensure_item_name_collection(task_id)

    # 5. 按 file_title 覆盖旧记录
    replace_item_name_record(item_name, dense_vector, sparse_vector, file_title, task_id)

    # 6. 回填 chunks 与 state
    _enrich_chunks_item_name(chunks, item_name)
    state["item_name"] = item_name
    state["chunks"] = chunks

    # 7. 返回 state
    logger.info(
        f"[提示] task_id={task_id} | 主体名称入库完成 "
        f"| item_name={item_name} | chunks={len(chunks)}"
    )
    return state


# ---------------------------------------------------------------------------
# 输入读取
# ---------------------------------------------------------------------------
@function_log(func_name="读取主体名称识别输入", return_names=["file_title", "chunks"])
def load_item_name_input(state: ImportGraphState) -> tuple[str, list[Chunk]]:
    """
    读取并校验 item_name 识别所需的输入.

    业务逻辑:
        1. 取 task_id file_title chunks md_path
        2. chunks 为空则读取切分备份
        3. 校验 chunks 非空
        4. 标题为空则用兜底标题
        5. 回写 state["chunks"] 与 state["file_title"]

    Args:
        state: 图全局状态.

    Returns:
        tuple[str, list[Chunk]]: 文件标题与切片列表.

    Raises:
        ValueError: chunks 与备份都为空.
    """
    # 1. 取 task_id file_title chunks md_path
    task_id: str = str(state.get("task_id", ""))
    file_title: str = str(state.get("file_title") or "").strip()
    chunks: list[Chunk] = state.get("chunks") or []
    md_path: str = str(state.get("md_path") or "")
    if not isinstance(chunks, list):
        raise business_error(
            ValueError, task_id, "chunks 类型非法", type=type(chunks).__name__
        )

    # 2. chunks 为空则读取切分备份
    if not chunks:
        chunks = _load_chunks_backup(md_path, task_id)

    # 3. 校验 chunks 非空
    if not chunks:
        raise business_error(ValueError, task_id, "chunks 为空且备份不可用", md_path=md_path)

    # 4. 标题为空则用兜底标题
    if not file_title:
        file_title = DEFAULT_FILE_TITLE
        logger.warning(f"[警告] task_id={task_id} | 文件标题为空, 用兜底标题 | {file_title}")

    # 5. 回写 state["chunks"] 与 state["file_title"]
    state["chunks"] = chunks
    state["file_title"] = file_title
    return file_title, chunks


def _load_chunks_backup(md_path: str, task_id: str) -> list[Chunk]:
    """
    从 md 同目录读取切分备份.

    先读新版 {stem}_chunks.json, 再兼容旧版 chunks.json.

    Args:
        md_path: Markdown 文件路径.
        task_id: 任务 ID, 只用于日志.

    Returns:
        list[Chunk]: 备份中的切片; 读取失败时返回空列表.
    """
    # 1. 校验 md_path 并拼出两个候选路径
    if not md_path.strip():
        logger.warning(f"[警告] task_id={task_id} | 缺少 md_path, 无法读取备份")
        return []
    md_path_po: Path = Path(md_path)
    if not md_path_po.is_file():
        logger.warning(f"[警告] task_id={task_id} | md 文件不存在, 无法读取备份 | md_path={md_path}")
        return []
    candidate_list: list[Path] = [
        md_path_po.with_name(f"{md_path_po.stem}{CHUNKS_JSON_SUFFIX}"),
        md_path_po.parent / LEGACY_CHUNKS_JSON_NAME,
    ]

    # 2. 逐个候选文件读取, 命中即返回
    for backup_path_po in candidate_list:
        if not backup_path_po.is_file():
            continue
        try:
            backup_data = json.loads(backup_path_po.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning(
                f"[警告] task_id={task_id} | 切分备份读取失败, 尝试下一个 "
                f"| path={backup_path_po} | error={exc}"
            )
            continue
        if isinstance(backup_data, list) and backup_data and all(
            isinstance(item, dict) for item in backup_data
        ):
            logger.info(
                f"[提示] task_id={task_id} | 已从备份恢复 chunks "
                f"| path={backup_path_po} | chunks={len(backup_data)}"
            )
            return backup_data
        logger.warning(f"[警告] task_id={task_id} | 备份内容为空或不是切片列表 | path={backup_path_po}")

    # 3. 没有可用备份
    return []


# ---------------------------------------------------------------------------
# 主体识别
# ---------------------------------------------------------------------------
@function_log(func_name="调用模型识别主体名称", return_names=["item_name"])
def recognize_item_name(chunks: list[Chunk], file_title: str, task_id: str) -> str:
    """
    调对话模型识别 item_name.

    业务逻辑:
        1. 取对话模型客户端
        2. 用前 K 个切片拼上下文并渲染提示词
        3. 调模型并提取文本
        4. 结果为空则用 file_title 兜底
        5. 清洗并返回 item_name

    Args:
        chunks: 文本切片.
        file_title: 文件标题, 兜底值.
        task_id: 任务 ID, 用于日志与异常.

    Returns:
        str: 识别出的主体名称.

    Raises:
        RuntimeError: 模型调用失败.
    """
    # 1. 取对话模型客户端
    llm_client = llm_provider.chat()

    # 2. 用前 K 个切片拼上下文并渲染提示词
    context: str = _build_chunk_context(chunks)
    recognition_prompt: str = load_prompt(
        PROMPT_ITEM_NAME_RECOGNITION,
        file_title=file_title,
        context=context,
    )

    # 3. 调模型并提取文本
    try:
        response = llm_client.invoke(recognition_prompt)
    except Exception as exc:
        raise business_error(RuntimeError, task_id, "主体名称识别调用失败", error=exc) from exc
    item_name: str = _parse_response_text(response)

    # 4. 结果为空则用 file_title 兜底
    if not item_name:
        logger.warning(f"[警告] task_id={task_id} | 未识别到 item_name, 用文件标题兜底")
        item_name = file_title

    # 5. 清洗并返回 item_name
    item_name = " ".join(item_name.split())
    if len(item_name) > ITEM_NAME_TEXT_MAX_LENGTH:
        logger.warning(
            f"[警告] task_id={task_id} | item_name 过长, 已截断 "
            f"| length={len(item_name)} | max={ITEM_NAME_TEXT_MAX_LENGTH}"
        )
        item_name = item_name[:ITEM_NAME_TEXT_MAX_LENGTH]
    logger.info(f"[提示] task_id={task_id} | item_name 识别完成 | item_name={item_name}")
    return item_name


def _build_chunk_context(chunks: list[Chunk]) -> str:
    """把前 K 个切片拼成模型可读的上下文."""
    context_lines: list[str] = []
    for chunk in chunks[:ITEM_NAME_RECOGNITION_CHUNKS_TOP_K]:
        parent_title: str = str(chunk.get("parent_title") or chunk.get("title") or "")
        part: Any = chunk.get("part", 1)
        content: str = str(chunk.get("content") or "")
        context_lines.append(f"父标题: {parent_title} | 第 {part} 部分 | 内容: {content}")
    return "\n".join(context_lines)


def _parse_response_text(response: Any) -> str:
    """从模型响应中提取纯文本, 兼容字符串与内容数组."""
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = [
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict)
        ]
        return "".join(text_parts).strip()
    return str(content or "").strip()


# ---------------------------------------------------------------------------
# 向量生成
# ---------------------------------------------------------------------------
@function_log(func_name="生成主体名称向量", return_names=["dense_vector", "sparse_vector"])
def embed_item_name(item_name: str, task_id: str) -> tuple[list[float], dict[int, float]]:
    """
    生成 item_name 的稠密与稀疏向量.

    业务逻辑:
        1. 调 BGE-M3 生成向量
        2. 取第一条稠密向量并校验维度
        3. 取第一条稀疏向量并校验非空
        4. 返回两个向量

    Args:
        item_name: 主体名称.
        task_id: 任务 ID, 用于日志与异常.

    Returns:
        tuple[list[float], dict[int, float]]: 稠密向量与稀疏向量.

    Raises:
        ValueError: BGE-M3 模型未配置或本地路径不存在.
        RuntimeError: 返回值缺字段或维度不匹配.
    """
    # 1. 调 BGE-M3 生成向量
    result = llm_provider.embed_texts([item_name])

    # 2. 取第一条稠密向量并校验维度
    dense_list: list[Any] = result.get("dense") or []
    dense_vector: Any = dense_list[0] if dense_list else []
    if not isinstance(dense_vector, list) or len(dense_vector) != ITEM_NAME_VECTOR_DIM:
        actual_dim = (
            len(dense_vector)
            if isinstance(dense_vector, list)
            else type(dense_vector).__name__
        )
        raise business_error(
            RuntimeError,
            task_id,
            "稠密向量维度不匹配",
            expected=ITEM_NAME_VECTOR_DIM,
            actual=actual_dim,
        )

    # 3. 取第一条稀疏向量并校验非空
    sparse_list: list[Any] = result.get("sparse") or []
    sparse_vector: Any = sparse_list[0] if sparse_list else {}
    if not isinstance(sparse_vector, dict) or not sparse_vector:
        raise business_error(RuntimeError, task_id, "稀疏向量为空或类型非法")

    # 4. 返回两个向量
    return dense_vector, sparse_vector


# ---------------------------------------------------------------------------
# Milvus 集合与写入
# ---------------------------------------------------------------------------
@function_log(func_name="准备 item_name 集合")
def ensure_item_name_collection(task_id: str) -> None:
    """
    确保 item_name 集合存在并可用.

    业务逻辑:
        1. 取客户端与集合名
        2. 集合已存在则直接返回
        3. 创建 schema 与索引
        4. 创建并加载集合

    Args:
        task_id: 任务 ID, 用于日志与异常.

    Raises:
        ValueError: 集合名未配置.
        RuntimeError: 检查或创建集合失败.
    """
    # 1. 取客户端与集合名
    milvus_client: MilvusClient = milvus_gateway.client
    collection_name: str = milvus_gateway.item_name_collection
    if not collection_name:
        raise business_error(ValueError, task_id, "item_name 集合名未配置", field="ITEM_NAME_COLLECTION")

    try:
        # 2. 集合已存在则直接返回
        if milvus_client.has_collection(collection_name=collection_name):
            logger.info(f"[提示] task_id={task_id} | item_name 集合已存在 | collection={collection_name}")
            return

        # 3. 创建 schema 与索引
        schema = milvus_client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(
            field_name=ITEM_NAME_FIELD_PK,
            datatype=DataType.INT64,
            nullable=False,
            is_primary=True,
        )
        schema.add_field(
            field_name=ITEM_NAME_FIELD_FILE_TITLE,
            datatype=DataType.VARCHAR,
            max_length=ITEM_NAME_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=ITEM_NAME_FIELD_ITEM_NAME,
            datatype=DataType.VARCHAR,
            max_length=ITEM_NAME_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=ITEM_NAME_FIELD_DENSE_VECTOR,
            datatype=DataType.FLOAT_VECTOR,
            dim=ITEM_NAME_VECTOR_DIM,
        )
        schema.add_field(
            field_name=ITEM_NAME_FIELD_SPARSE_VECTOR,
            datatype=DataType.SPARSE_FLOAT_VECTOR,
        )

        index_params = milvus_client.prepare_index_params()
        index_params.add_index(
            field_name=ITEM_NAME_FIELD_DENSE_VECTOR,
            index_type=ITEM_NAME_DENSE_INDEX_TYPE,
            index_name=ITEM_NAME_DENSE_INDEX_NAME,
            metric_type=ITEM_NAME_DENSE_METRIC_TYPE,
            index_params={
                "M": ITEM_NAME_HNSW_M,
                "efConstruction": ITEM_NAME_HNSW_EF_CONSTRUCTION,
            },
        )
        index_params.add_index(
            field_name=ITEM_NAME_FIELD_SPARSE_VECTOR,
            index_type=ITEM_NAME_SPARSE_INDEX_TYPE,
            index_name=ITEM_NAME_SPARSE_INDEX_NAME,
            metric_type=ITEM_NAME_SPARSE_METRIC_TYPE,
            index_params={"inverted_index_algo": ITEM_NAME_SPARSE_INVERTED_ALGO},
        )

        # 4. 创建并加载集合
        milvus_client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
        )
        milvus_client.load_collection(collection_name=collection_name)
    except Exception as exc:
        raise business_error(
            RuntimeError, task_id, "准备 item_name 集合失败", collection=collection_name, error=exc
        ) from exc

    logger.info(
        f"[提示] task_id={task_id} | item_name 集合创建完成 "
        f"| collection={collection_name} | dim={ITEM_NAME_VECTOR_DIM}"
    )


@function_log(func_name="覆盖 item_name 向量记录")
def replace_item_name_record(
    item_name: str,
    dense_vector: list[float],
    sparse_vector: dict[int, float],
    file_title: str,
    task_id: str,
) -> None:
    """
    按 file_title 覆盖 item_name 向量记录.

    业务逻辑:
        1. 删除同 file_title 的旧记录
        2. 组装新记录并插入
        3. 记录条数日志

    Args:
        item_name: 主体名称.
        dense_vector: 稠密向量.
        sparse_vector: 稀疏向量.
        file_title: 文件标题, 作为覆盖条件.
        task_id: 任务 ID, 用于日志与异常.

    Raises:
        RuntimeError: 删除或插入失败.
    """
    # 1. 删除同 file_title 的旧记录
    milvus_client: MilvusClient = milvus_gateway.client
    collection_name: str = milvus_gateway.item_name_collection
    filter_expr: str = f"file_title == '{_escape_filter_value(file_title)}'"
    try:
        delete_result = milvus_client.delete(
            collection_name=collection_name,
            filter=filter_expr,
        )
    except Exception as exc:
        raise business_error(
            RuntimeError, task_id, "item_name 旧记录删除失败", collection=collection_name, error=exc
        ) from exc
    logger.info(
        f"[提示] task_id={task_id} | item_name 旧记录已删除 "
        f"| count={delete_result.get('delete_count', 0)}"
    )

    # 2. 组装新记录并插入
    record: dict[str, Any] = {
        ITEM_NAME_FIELD_FILE_TITLE: file_title,
        ITEM_NAME_FIELD_ITEM_NAME: item_name,
        ITEM_NAME_FIELD_DENSE_VECTOR: dense_vector,
        ITEM_NAME_FIELD_SPARSE_VECTOR: sparse_vector,
    }
    try:
        insert_result = milvus_client.insert(
            collection_name=collection_name,
            data=[record],
        )
    except Exception as exc:
        raise business_error(
            RuntimeError, task_id, "item_name 记录插入失败", collection=collection_name, error=exc
        ) from exc

    # 3. 记录条数日志
    logger.info(
        f"[提示] task_id={task_id} | item_name 记录已插入 "
        f"| count={insert_result.get('insert_count', 0)} | item_name={item_name}"
    )


def _escape_filter_value(value: str) -> str:
    """转义 Milvus 过滤表达式里的字符串值."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _enrich_chunks_item_name(chunks: list[Chunk], item_name: str) -> None:
    """把 item_name 回填到每个切片."""
    for chunk in chunks:
        chunk["item_name"] = item_name
