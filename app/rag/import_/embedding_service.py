"""
切片向量化服务.

职责: 读取 chunks, 按批调用 BGE-M3 生成稠密与稀疏向量并回填.
边界: 不负责切分与 Milvus 入库, 不建集合.
"""
from typing import Any

from app.constants.embedding_constants import (
    BGE_M3_VECTOR_DIM,
    CHUNK_FIELD_DENSE_VECTOR,
    CHUNK_FIELD_SPARSE_VECTOR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_TEXT_SEPARATOR,
)
from app.infra.llm.providers import llm_provider
from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import function_log, logger

# 切片字典, 与 split_document 的输出保持一致
Chunk = dict[str, Any]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
@function_log(func_name="批量生成切片向量", return_names=["state"])
def generate_chunk_embeddings(state: ImportGraphState) -> ImportGraphState:
    """
    切片向量化主入口.

    业务逻辑:
        1. 读取并校验 chunks
        2. 取 item_name 兜底值
        3. 按批生成并回填向量
        4. 回写 state["embeddings_content"]
        5. 返回 state

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 embeddings_content 的状态.

    Raises:
        ValueError: chunks 为空或类型非法, 切片缺少文本.
        RuntimeError: 模型返回的向量数量或维度不匹配.
    """
    task_id: str = str(state.get("task_id", ""))

    # 1. 读取并校验 chunks
    chunks: list[Chunk] = get_chunks(state)

    # 2. 取 item_name 兜底值
    default_item_name: str = str(state.get("item_name") or state.get("file_title") or "")

    # 3. 按批生成并回填向量
    embed_chunks_in_batches(chunks, default_item_name, task_id)

    # 4. 回写 state["embeddings_content"]
    state["embeddings_content"] = chunks

    # 5. 返回 state
    logger.info(
        f"[提示] task_id={task_id} | 切片向量化完成 "
        f"| chunks={len(chunks)} | dim={BGE_M3_VECTOR_DIM}"
    )
    return state


# ---------------------------------------------------------------------------
# 输入读取
# ---------------------------------------------------------------------------
@function_log(func_name="读取待向量化切片", return_names=["chunks"])
def get_chunks(state: ImportGraphState) -> list[Chunk]:
    """
    读取并校验待向量化的 chunks.

    业务逻辑:
        1. 从 state 取 task_id 与 chunks
        2. 校验 chunks 是非空列表
        3. 返回 chunks

    Args:
        state: 图全局状态.

    Returns:
        list[Chunk]: 待向量化的切片.

    Raises:
        ValueError: chunks 为空, 不是 list, 或元素不是 dict.
    """
    # 1. 从 state 取 task_id 与 chunks
    task_id: str = str(state.get("task_id", ""))
    chunks: list[Chunk] = state.get("chunks") or []

    # 2. 校验 chunks 是非空列表
    if not isinstance(chunks, list):
        raise business_error(
            ValueError, task_id, "chunks 类型非法", type=type(chunks).__name__
        )
    if not chunks:
        raise business_error(ValueError, task_id, "chunks 为空, 无法向量化")
    if not all(isinstance(chunk, dict) for chunk in chunks):
        raise business_error(ValueError, task_id, "chunks 元素类型非法")

    # 3. 返回 chunks
    return chunks


# ---------------------------------------------------------------------------
# 批量向量化
# ---------------------------------------------------------------------------
@function_log(func_name="按批生成切片向量")
def embed_chunks_in_batches(
    chunks: list[Chunk],
    default_item_name: str,
    task_id: str,
) -> None:
    """
    按批生成切片向量并回填.

    业务逻辑:
        1. 计算总片数与批次数
        2. 按 EMBEDDING_BATCH_SIZE 截取子片
        3. 拼接 item_name 与 content, 得到待向量化文本
        4. 调 BGE-M3 生成向量并校验数量与维度
        5. 回填 dense_vector 与 sparse_vector

    副作用:
        修改 chunks 中每个切片的 dense_vector 与 sparse_vector.

    Args:
        chunks: 待向量化切片.
        default_item_name: 切片缺少 item_name 时的兜底值.
        task_id: 任务 ID, 用于日志与异常.

    Raises:
        ValueError: 切片缺少可向量化文本.
        RuntimeError: 向量数量或维度不匹配.
    """
    # 1. 计算总片数与批次数
    total: int = len(chunks)
    batch_count: int = (total + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    logger.info(
        f"[提示] task_id={task_id} | 切片向量化开始 "
        f"| total={total} | batch_size={EMBEDDING_BATCH_SIZE} | batches={batch_count}"
    )

    # 2. 按 EMBEDDING_BATCH_SIZE 截取子片
    for batch_index in range(batch_count):
        start: int = batch_index * EMBEDDING_BATCH_SIZE
        end: int = min(start + EMBEDDING_BATCH_SIZE, total)
        sub_chunks: list[Chunk] = chunks[start:end]
        logger.debug(
            f"[调试] task_id={task_id} | 处理批次 "
            f"| batch={batch_index + 1}/{batch_count} | range={start}-{end}"
        )

        # 3. 拼接 item_name 与 content, 得到待向量化文本
        text_list: list[str] = []
        for offset, chunk in enumerate(sub_chunks):
            embedding_text: str = _build_embedding_text(chunk, default_item_name)
            if not embedding_text:
                raise business_error(
                    ValueError,
                    task_id,
                    "切片缺少 item_name 与 content",
                    index=start + offset,
                )
            text_list.append(embedding_text)

        # 4. 调 BGE-M3 生成向量并校验数量与维度
        result = llm_provider.embed_texts(text_list)
        dense_list: list[Any] = result.get("dense") or []
        sparse_list: list[Any] = result.get("sparse") or []
        _validate_embedding_result(
            dense_list,
            sparse_list,
            len(sub_chunks),
            task_id,
            batch_index,
        )

        # 5. 回填 dense_vector 与 sparse_vector
        for offset, chunk in enumerate(sub_chunks):
            chunk[CHUNK_FIELD_DENSE_VECTOR] = dense_list[offset]
            chunk[CHUNK_FIELD_SPARSE_VECTOR] = sparse_list[offset]


def _build_embedding_text(chunk: Chunk, default_item_name: str) -> str:
    """拼接 item_name 与 content, 缺少 item_name 时用默认值."""
    item_name: str = str(chunk.get("item_name") or default_item_name or "").strip()
    content: str = str(chunk.get("content") or "").strip()
    if item_name and content:
        return f"{item_name}{EMBEDDING_TEXT_SEPARATOR}{content}"
    return content or item_name


def _validate_embedding_result(
    dense_list: list[Any],
    sparse_list: list[Any],
    expected_count: int,
    task_id: str,
    batch_index: int,
) -> None:
    """校验向量数量 稠密维度与稀疏向量非空."""
    if len(dense_list) != expected_count or len(sparse_list) != expected_count:
        raise business_error(
            RuntimeError,
            task_id,
            "向量数量与切片数量不匹配",
            batch=batch_index + 1,
            expected=expected_count,
            dense=len(dense_list),
            sparse=len(sparse_list),
        )

    for offset in range(expected_count):
        dense_vector: Any = dense_list[offset]
        sparse_vector: Any = sparse_list[offset]
        if not isinstance(dense_vector, list) or len(dense_vector) != BGE_M3_VECTOR_DIM:
            actual_dim = (
                len(dense_vector)
                if isinstance(dense_vector, list)
                else type(dense_vector).__name__
            )
            raise business_error(
                RuntimeError,
                task_id,
                "稠密向量维度不匹配",
                batch=batch_index + 1,
                index=offset,
                expected=BGE_M3_VECTOR_DIM,
                actual=actual_dim,
            )
        if not isinstance(sparse_vector, dict) or not sparse_vector:
            raise business_error(
                RuntimeError,
                task_id,
                "稀疏向量为空或类型非法",
                batch=batch_index + 1,
                index=offset,
            )
