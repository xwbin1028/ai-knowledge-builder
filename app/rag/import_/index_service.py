"""
入库服务模块。

纯函数服务，负责 Milvus 集合的 Schema 准备、旧数据清理与批量插入，
将向量化后的切片数据持久化到向量数据库。
"""
from app.process.import_.agent.state import ImportGraphState


def index_chunks(state: ImportGraphState) -> ImportGraphState:
    """
    入库服务。

    执行步骤：
        1. 准备集合 Schema 和索引。
        2. 根据 item_name 删除旧数据。
        3. 批量插入新的 chunks。
        4. 回写 chunk_id 等入库结果。

    Args:
        state (ImportGraphState): 图全局状态。

    Returns:
        ImportGraphState: 更新后的图全局状态。
    """
    return state
