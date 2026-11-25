"""
切片入库服务.

职责: 准备 chunks 集合, 按 file_title 覆盖旧记录, 批量写入带向量的切片并回显 chunk_id.
边界: 不负责切分与向量生成, 不维护 item_name 集合.
"""
from typing import Any

from pymilvus import DataType, MilvusClient

from app.constants.embedding_constants import (
    BGE_M3_VECTOR_DIM,
    CHUNK_FIELD_DENSE_VECTOR,
    CHUNK_FIELD_SPARSE_VECTOR,
)
from app.constants.index_constants import (
    CHUNK_CONTENT_MAX_LENGTH,
    CHUNK_DENSE_INDEX_NAME,
    CHUNK_DENSE_INDEX_TYPE,
    CHUNK_DENSE_METRIC_TYPE,
    CHUNK_FIELD_CHUNK_ID,
    CHUNK_FIELD_CONTENT,
    CHUNK_FIELD_FILE_TITLE,
    CHUNK_FIELD_ITEM_NAME,
    CHUNK_FIELD_PARENT_TITLE,
    CHUNK_FIELD_PART,
    CHUNK_FIELD_TITLE,
    CHUNK_HNSW_EF_CONSTRUCTION,
    CHUNK_HNSW_M,
    CHUNK_SPARSE_INDEX_NAME,
    CHUNK_SPARSE_INDEX_TYPE,
    CHUNK_SPARSE_INVERTED_ALGO,
    CHUNK_SPARSE_METRIC_TYPE,
    CHUNK_TEXT_MAX_LENGTH,
)
from app.infra.vectorstore.milvus_gateway import milvus_gateway
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import function_log, logger

# 切片字典, 与 split_document 的输出保持一致
Chunk = dict[str, Any]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="写入切片向量索引", return_names=["state"])
def index_chunks(state: ImportGraphState) -> ImportGraphState:
    """
    切片入库主入口.

    业务逻辑:
        1. 读取并校验 embeddings_content
        2. 确定本次覆盖的 file_title 与 item_name 兜底值
        3. 确保 chunks 集合可用
        4. 按 file_title 覆盖旧记录并回显 chunk_id
        5. 回写 state 的 file_title chunks 与 embeddings_content
        6. 返回 state

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已回显 chunk_id 的状态.

    Raises:
        ValueError: embeddings_content 为空, 或 file_title 为空.
        RuntimeError: 集合准备或数据写入失败.
    """
    task_id: str = str(state.get("task_id", ""))

    # 1. 读取并校验 embeddings_content
    embeddings_content: list[Chunk] = get_embeddings_content(state)

    # 2. 确定本次覆盖的 file_title 与 item_name 兜底值
    file_title: str = resolve_file_title(state, embeddings_content, task_id)
    default_item_name: str = str(state.get("item_name") or file_title)

    # 3. 确保 chunks 集合可用
    ensure_chunks_collection(task_id)

    # 4. 按 file_title 覆盖旧记录并回显 chunk_id
    replace_chunks_records(embeddings_content, file_title, default_item_name, task_id)

    # 5. 回写 state 的 file_title chunks 与 embeddings_content
    state["file_title"] = file_title
    state["chunks"] = embeddings_content
    state["embeddings_content"] = embeddings_content

    # 6. 返回 state
    logger.info(
        f"[提示] task_id={task_id} | 切片入库完成 "
        f"| file_title={file_title} | chunks={len(embeddings_content)}"
    )
    return state


# ---------------------------------------------------------------------------
# 输入读取
# ---------------------------------------------------------------------------
@function_log(func_name="读取待入库切片", return_names=["embeddings_content"])
def get_embeddings_content(state: ImportGraphState) -> list[Chunk]:
    """
    读取并校验待入库切片.

    业务逻辑:
        1. 从 state 取 task_id 与 embeddings_content
        2. 校验非空且元素为 dict
        3. 返回 embeddings_content

    Args:
        state: 图全局状态.

    Returns:
        list[Chunk]: 带向量的切片.

    Raises:
        ValueError: embeddings_content 为空, 不是 list, 或元素不是 dict.
    """
    # 1. 从 state 取 task_id 与 embeddings_content
    task_id: str = str(state.get("task_id", ""))
    embeddings_content: list[Chunk] = state.get("embeddings_content") or []

    # 2. 校验非空且元素为 dict
    if not isinstance(embeddings_content, list):
        raise business_error(
            ValueError, task_id, "embeddings_content 类型非法", type=type(embeddings_content).__name__
        )
    if not embeddings_content:
        raise business_error(ValueError, task_id, "embeddings_content 为空, 无法入库")
    if not all(isinstance(chunk, dict) for chunk in embeddings_content):
        raise business_error(ValueError, task_id, "embeddings_content 元素类型非法")

    # 3. 返回 embeddings_content
    return embeddings_content


@function_log(func_name="确定本次覆盖的文件标题", return_names=["file_title"])
def resolve_file_title(
    state: ImportGraphState,
    embeddings_content: list[Chunk],
    task_id: str,
) -> str:
    """
    确定本次覆盖的 file_title.

    业务逻辑:
        1. 优先取 state 的 file_title
        2. 缺失则取第一个切片的 file_title
        3. 都为空则终止
        4. 截断过长标题并回写每个切片

    副作用:
        回写 embeddings_content 中每个切片的 file_title.

    Args:
        state: 图全局状态.
        embeddings_content: 带向量的切片.
        task_id: 任务 ID, 用于日志与异常.

    Returns:
        str: 本次覆盖使用的文件标题.

    Raises:
        ValueError: file_title 为空.
    """
    # 1. 优先取 state 的 file_title
    file_title: str = str(state.get("file_title") or "").strip()

    # 2. 缺失则取第一个切片的 file_title
    if not file_title:
        file_title = str(embeddings_content[0].get(CHUNK_FIELD_FILE_TITLE) or "").strip()

    # 3. 都为空则终止
    if not file_title:
        raise business_error(ValueError, task_id, "file_title 为空, 无法覆盖旧数据")

    # 4. 截断过长标题并回写每个切片
    if len(file_title) > CHUNK_TEXT_MAX_LENGTH:
        logger.warning(
            f"[警告] task_id={task_id} | file_title 超长, 已截断 "
            f"| length={len(file_title)} | max={CHUNK_TEXT_MAX_LENGTH}"
        )
        file_title = file_title[:CHUNK_TEXT_MAX_LENGTH]
    for chunk in embeddings_content:
        chunk[CHUNK_FIELD_FILE_TITLE] = file_title
    return file_title


# ---------------------------------------------------------------------------
# Milvus 集合与写入
# ---------------------------------------------------------------------------
@function_log(func_name="准备 chunks 集合")
def ensure_chunks_collection(task_id: str) -> None:
    """
    确保 chunks 集合存在并可用.

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
    collection_name: str = milvus_gateway.chunks_collection
    if not collection_name:
        raise business_error(ValueError, task_id, "chunks 集合名未配置", field="CHUNKS_COLLECTION")

    try:
        # 2. 集合已存在则直接返回
        if milvus_client.has_collection(collection_name=collection_name):
            logger.info(f"[提示] task_id={task_id} | chunks 集合已存在 | collection={collection_name}")
            return

        # 3. 创建 schema 与索引
        schema = milvus_client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(
            field_name=CHUNK_FIELD_CHUNK_ID,
            datatype=DataType.INT64,
            nullable=False,
            is_primary=True,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_FILE_TITLE,
            datatype=DataType.VARCHAR,
            max_length=CHUNK_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_ITEM_NAME,
            datatype=DataType.VARCHAR,
            max_length=CHUNK_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_PARENT_TITLE,
            datatype=DataType.VARCHAR,
            max_length=CHUNK_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_TITLE,
            datatype=DataType.VARCHAR,
            max_length=CHUNK_TEXT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_PART,
            datatype=DataType.INT32,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_CONTENT,
            datatype=DataType.VARCHAR,
            max_length=CHUNK_CONTENT_MAX_LENGTH,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_DENSE_VECTOR,
            datatype=DataType.FLOAT_VECTOR,
            dim=BGE_M3_VECTOR_DIM,
        )
        schema.add_field(
            field_name=CHUNK_FIELD_SPARSE_VECTOR,
            datatype=DataType.SPARSE_FLOAT_VECTOR,
        )

        index_params = milvus_client.prepare_index_params()
        index_params.add_index(
            field_name=CHUNK_FIELD_DENSE_VECTOR,
            index_type=CHUNK_DENSE_INDEX_TYPE,
            index_name=CHUNK_DENSE_INDEX_NAME,
            metric_type=CHUNK_DENSE_METRIC_TYPE,
            index_params={
                "M": CHUNK_HNSW_M,
                "efConstruction": CHUNK_HNSW_EF_CONSTRUCTION,
            },
        )
        index_params.add_index(
            field_name=CHUNK_FIELD_SPARSE_VECTOR,
            index_type=CHUNK_SPARSE_INDEX_TYPE,
            index_name=CHUNK_SPARSE_INDEX_NAME,
            metric_type=CHUNK_SPARSE_METRIC_TYPE,
            index_params={"inverted_index_algo": CHUNK_SPARSE_INVERTED_ALGO},
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
            RuntimeError, task_id, "准备 chunks 集合失败", collection=collection_name, error=exc
        ) from exc

    logger.info(
        f"[提示] task_id={task_id} | chunks 集合创建完成 "
        f"| collection={collection_name} | dim={BGE_M3_VECTOR_DIM}"
    )


@function_log(func_name="覆盖切片向量记录")
def replace_chunks_records(
    embeddings_content: list[Chunk],
    file_title: str,
    default_item_name: str,
    task_id: str,
) -> None:
    """
    按 file_title 覆盖 chunks 集合记录.

    业务逻辑:
        1. 组装并校验插入记录
        2. 删除同 file_title 的旧记录
        3. 批量插入
        4. 回显 chunk_id 并校验数量

    副作用:
        给 embeddings_content 中每个切片写入 chunk_id.

    Args:
        embeddings_content: 带向量的切片.
        file_title: 文件标题, 作为覆盖条件.
        default_item_name: 切片缺少 item_name 时的兜底值.
        task_id: 任务 ID, 用于日志与异常.

    Raises:
        ValueError: 切片字段非法.
        RuntimeError: 删除或插入失败, 或 chunk_id 数量不匹配.
    """
    # 1. 组装并校验插入记录
    #    先校验再删旧数据, 避免切片非法时把旧数据删掉
    insert_data: list[dict[str, Any]] = [
        _build_chunk_record(chunk, file_title, default_item_name, task_id, index)
        for index, chunk in enumerate(embeddings_content)
    ]

    # 2. 删除同 file_title 的旧记录
    milvus_client: MilvusClient = milvus_gateway.client
    collection_name: str = milvus_gateway.chunks_collection
    filter_expr: str = f"file_title == '{_escape_filter_value(file_title)}'"
    try:
        delete_result = milvus_client.delete(
            collection_name=collection_name,
            filter=filter_expr,
        )
    except Exception as exc:
        raise business_error(
            RuntimeError, task_id, "切片旧记录删除失败", collection=collection_name, error=exc
        ) from exc
    logger.info(
        f"[提示] task_id={task_id} | 切片旧记录已删除 "
        f"| count={delete_result.get('delete_count', 0)}"
    )

    # 3. 批量插入
    #    旧记录已删除, 清理上一轮残留的 chunk_id, 避免状态里留下失效主键
    for chunk in embeddings_content:
        chunk.pop(CHUNK_FIELD_CHUNK_ID, None)
    try:
        insert_result = milvus_client.insert(
            collection_name=collection_name,
            data=insert_data,
        )
    except Exception as exc:
        raise business_error(
            RuntimeError, task_id, "切片记录插入失败", collection=collection_name, error=exc
        ) from exc

    # 4. 回显 chunk_id 并校验数量
    chunk_id_list: list[Any] = list(insert_result.get("ids") or [])
    if len(chunk_id_list) != len(embeddings_content):
        raise business_error(
            RuntimeError,
            task_id,
            "chunk_id 数量与切片数量不匹配",
            expected=len(embeddings_content),
            actual=len(chunk_id_list),
        )
    for chunk, chunk_id in zip(embeddings_content, chunk_id_list):
        chunk[CHUNK_FIELD_CHUNK_ID] = chunk_id

    logger.info(
        f"[提示] task_id={task_id} | 切片记录已插入 "
        f"| count={insert_result.get('insert_count', 0)} | ids={len(chunk_id_list)}"
    )


def _build_chunk_record(
    chunk: Chunk,
    file_title: str,
    default_item_name: str,
    task_id: str,
    index: int,
) -> dict[str, Any]:
    """组装单条插入记录, 校验向量与标量字段."""
    dense_vector: Any = chunk.get(CHUNK_FIELD_DENSE_VECTOR)
    if not isinstance(dense_vector, list) or len(dense_vector) != BGE_M3_VECTOR_DIM:
        actual_dim = (
            len(dense_vector)
            if isinstance(dense_vector, list)
            else type(dense_vector).__name__
        )
        raise business_error(
            RuntimeError,
            task_id,
            "稠密向量缺失或维度不匹配",
            index=index,
            expected=BGE_M3_VECTOR_DIM,
            actual=actual_dim,
        )

    sparse_vector: Any = chunk.get(CHUNK_FIELD_SPARSE_VECTOR)
    if not isinstance(sparse_vector, dict) or not sparse_vector:
        raise business_error(RuntimeError, task_id, "稀疏向量缺失或为空", index=index)

    try:
        part: int = int(chunk.get(CHUNK_FIELD_PART, 1))
    except (TypeError, ValueError) as exc:
        raise business_error(ValueError, task_id, "part 不是整数", index=index) from exc
    if part < 1:
        raise business_error(ValueError, task_id, "part 必须大于等于 1", index=index, part=part)

    title: str = _truncate_text(
        chunk.get(CHUNK_FIELD_TITLE) or file_title,
        CHUNK_TEXT_MAX_LENGTH,
        CHUNK_FIELD_TITLE,
        task_id,
        index,
    )
    parent_title: str = _truncate_text(
        chunk.get(CHUNK_FIELD_PARENT_TITLE) or title,
        CHUNK_TEXT_MAX_LENGTH,
        CHUNK_FIELD_PARENT_TITLE,
        task_id,
        index,
    )
    item_name: str = _truncate_text(
        chunk.get(CHUNK_FIELD_ITEM_NAME) or default_item_name,
        CHUNK_TEXT_MAX_LENGTH,
        CHUNK_FIELD_ITEM_NAME,
        task_id,
        index,
    )
    content: str = _truncate_text(
        chunk.get(CHUNK_FIELD_CONTENT) or "",
        CHUNK_CONTENT_MAX_LENGTH,
        CHUNK_FIELD_CONTENT,
        task_id,
        index,
    )
    if not content:
        raise business_error(ValueError, task_id, "content 为空, 无法入库", index=index)

    return {
        CHUNK_FIELD_FILE_TITLE: file_title,
        CHUNK_FIELD_ITEM_NAME: item_name,
        CHUNK_FIELD_PARENT_TITLE: parent_title,
        CHUNK_FIELD_TITLE: title,
        CHUNK_FIELD_PART: part,
        CHUNK_FIELD_CONTENT: content,
        CHUNK_FIELD_DENSE_VECTOR: dense_vector,
        CHUNK_FIELD_SPARSE_VECTOR: sparse_vector,
    }


def _truncate_text(
    value: Any,
    max_length: int,
    field_name: str,
    task_id: str,
    index: int,
) -> str:
    """转字符串并截断到最大长度, 截断时记 warning."""
    text: str = str(value or "").strip()
    if len(text) <= max_length:
        return text
    logger.warning(
        f"[警告] task_id={task_id} | {field_name} 超长, 已截断 "
        f"| index={index} | length={len(text)} | max={max_length}"
    )
    return text[:max_length]


def _escape_filter_value(value: str) -> str:
    """转义 Milvus 过滤表达式里的字符串值."""
    return value.replace("\\", "\\\\").replace("'", "\\'")
