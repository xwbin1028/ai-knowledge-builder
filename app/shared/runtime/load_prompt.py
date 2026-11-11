"""
提示词加载与渲染工具模块。

提供从项目资源目录加载文本提示词 (Prompt)，并动态渲染变量占位符的能力。
支持通过传入关键字参数替换提示词模板中的 ``{变量名}``，便于业务侧复用统一模板。
"""
from app.shared.runtime.logger import logger, PROJECT_ROOT


# ---------------------------------------------------------------------------
# 核心方法
# ---------------------------------------------------------------------------
def load_prompt(name: str, **kwargs) -> str:
    """加载提示词文件并渲染变量占位符。

    根据传入的模板名称，从项目资源目录中读取对应的 .prompt 文件；
    若传入了关键字参数，则使用 Python 的 str.format 机制替换模板中的占位符。

    Args:
        name (str): 提示词文件名 (不带 .prompt 后缀，如 "image_summary")。
        **kwargs: 需要渲染的变量键值对。键名必须与 .prompt 文件中的占位符完全一致。
                  例如：root_folder="测试文件", image_content=("上文", "下文")。

    Returns:
        str: 渲染后的最终提示词字符串；若未传参，则返回原始文本。

    Raises:
        FileNotFoundError: 当指定的提示词文件不存在时抛出。
    """
    # 1. 拼接提示词文件路径 (基于项目根目录定位)
    prompt_path = PROJECT_ROOT / 'app' / 'resources' / 'prompts' / f'{name}.prompt'

    # 2. 前置校验文件是否存在，避免读取时抛出不可读的底层 IO 错误
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在：{prompt_path.absolute()}")

    # 3. 读取纯文本提示词，强制使用 UTF-8 编码避免中文乱码
    raw_prompt = prompt_path.read_text(encoding='utf-8')

    # 4. 如果传入了参数，执行占位符渲染；否则直接返回原文本
    if kwargs:
        rendered_prompt = raw_prompt.format(**kwargs)
        # 记录渲染日志，便于排查模板变量替换问题
        logger.debug(f"提示词渲染成功，替换变量：{list(kwargs.keys())}")
        return rendered_prompt
    return raw_prompt
