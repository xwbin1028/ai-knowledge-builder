"""
图节点名常量.

节点名只在这里定义, 图编排 节点文件 进度映射统一引用, 避免三处写错.
"""
from typing import Final

# 导入流程
NODE_ENTRY: Final[str] = "node_entry"
NODE_PDF_TO_MD: Final[str] = "node_pdf_to_md"
NODE_MD_IMG: Final[str] = "node_md_img"
NODE_ITEM_NAME_RECOGNITION: Final[str] = "node_item_name_recognition"
NODE_DOCUMENT_SPLIT: Final[str] = "node_document_split"
NODE_BGE_EMBEDDING: Final[str] = "node_bge_embedding"
NODE_IMPORT_MILVUS: Final[str] = "node_import_milvus"

# 查询流程, 待实现
NODE_ITEM_NAME_CONFIRM: Final[str] = "node_item_name_confirm"
NODE_ANSWER_OUTPUT: Final[str] = "node_answer_output"
NODE_RERANK: Final[str] = "node_rerank"
NODE_RRF: Final[str] = "node_rrf"
NODE_WEB_SEARCH_MCP: Final[str] = "node_web_search_mcp"
NODE_SEARCH_EMBEDDING: Final[str] = "node_search_embedding"
NODE_SEARCH_EMBEDDING_HYDE: Final[str] = "node_search_embedding_hyde"
NODE_MULTI_SEARCH: Final[str] = "node_multi_search"
NODE_QUERY_KG: Final[str] = "node_query_kg"
NODE_JOIN: Final[str] = "node_join"

# 结束节点, LangGraph 的 END 值为 __end__
NODE_END: Final[str] = "__end__"
