"""
提示词加载与渲染.

从 app/resources/prompts 读取 .prompt 文件, 用 str.format 渲染 {变量} 占位符.
"""
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import PROJECT_ROOT, logger

# 提示词目录, 基于项目根目录定位
_PROMPT_DIR = PROJECT_ROOT / "app" / "resources" / "prompts"


def load_prompt(name: str, **kwargs) -> str:
    """
    加载提示词并渲染占位符.

    业务逻辑:
        1. 拼出 .prompt 路径
        2. 校验文件存在
        3. 读取 UTF-8 文本
        4. 有参数则渲染, 否则原样返回

    Args:
        name: 提示词文件名, 不带 .prompt 后缀.
        **kwargs: 占位符键值对, 键名必须与模板一致.

    Returns:
        str: 渲染后的提示词.

    Raises:
        FileNotFoundError: 提示词文件不存在.
        KeyError: 模板占位符与入参不匹配.
    """
    # 1. 拼出 .prompt 路径
    prompt_path = _PROMPT_DIR / f"{name}.prompt"

    # 2. 校验文件存在, 避免底层 IO 报错难读
    if not prompt_path.exists():
        raise business_error(FileNotFoundError, "", "提示词文件不存在", path=prompt_path)

    # 3. 读取 UTF-8 文本, 避免中文乱码
    raw_prompt = prompt_path.read_text(encoding="utf-8")

    # 4. 有参数则渲染, 否则原样返回
    if not kwargs:
        return raw_prompt
    logger.debug(f"[调试] 提示词渲染 | name={name} | keys={list(kwargs.keys())}")
    return raw_prompt.format(**kwargs)
