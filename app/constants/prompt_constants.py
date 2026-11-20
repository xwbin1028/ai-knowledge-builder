"""
提示词文件名常量.

值即 app/resources/prompts/<name>.prompt 的 <name>, 不写后缀.
"""
from typing import Final

PROMPT_ANSWER_OUT: Final[str] = "answer_out"
PROMPT_HYDE: Final[str] = "hyde"
PROMPT_IMAGE_SUMMARY: Final[str] = "image_summary"
PROMPT_ITEM_NAME_RECOGNITION: Final[str] = "item_name_recognition"
PROMPT_PRODUCT_RECOGNITION_SYSTEM: Final[str] = "product_recognition_system"
PROMPT_RERANK_TEXT_REFINE: Final[str] = "rerank_text_refine"
PROMPT_REWRITTEN_QUERY_AND_ITEM_NAMES: Final[str] = "rewritten_query_and_item_names"
