# 05 模板 template

用法: 复制骨架, 改 3 处: 模块名 函数名 字段名; 删掉用不到的分区.
新建文件流程: 选骨架 -> 改名 -> 写步骤 -> 跑 compileall -> 更新 06-map.

## A 模块头

```python
"""
<领域> 服务.

职责: <一句话>.
边界: 不负责 <xxx>, 由 <yyy> 承担.
"""
```

小文件只留一句话加职责, 不写"主要特性".

## B 图节点

```python
"""
节点: PDF 转 Markdown.

读取 state 的 pdf_path, 调用 MinerU 解析, 回写 md_path.
"""
from app.constants.node_constants import NODE_PDF_TO_MD
from app.process.import_.agent.state import ImportGraphState
from app.rag.import_.pdf_parse_service import parse_pdf_to_markdown
from app.shared.runtime.logger import node_log
from app.shared.utils.task_utils import add_done_task, add_running_task


@node_log(NODE_PDF_TO_MD)
def node_pdf_to_md(state: ImportGraphState) -> ImportGraphState:
    """
    节点: PDF 转 Markdown.

    Args:
        state: 图全局状态.

    Returns:
        ImportGraphState: 已写入 md_path 的状态.
    """
    add_running_task(state["task_id"], NODE_PDF_TO_MD)
    state = parse_pdf_to_markdown(state)
    add_done_task(state["task_id"], NODE_PDF_TO_MD)
    return state
```

## C 服务函数

```python
from pathlib import Path

from app.process.import_.agent.state import ImportGraphState
from app.shared.runtime.error_utils import business_error
from app.shared.runtime.logger import function_log


@function_log(func_name="校验并读取 Markdown", return_names=["md_path_po", "md_content"])
def read_markdown(state: ImportGraphState) -> tuple[Path, str]:
    """
    校验并读取 Markdown.

    业务逻辑:
        1. 从 state 取 md_path 并校验
        2. 转 Path 并校验文件存在
        3. 读取正文并回写 state

    Args:
        state: 图全局状态.

    Returns:
        tuple[Path, str]: md 文件与正文.

    Raises:
        ValueError: md_path 为空.
        FileNotFoundError: md 文件不存在.
    """
    # 1. 从 state 取 md_path 并校验
    task_id: str = state.get("task_id", "")
    md_path: str = state.get("md_path", "")
    if not md_path.strip():
        raise business_error(ValueError, task_id, "Markdown 路径为空", md_path=md_path)

    # 2. 转 Path 并校验文件存在
    md_path_po: Path = Path(md_path)
    if not md_path_po.is_file():
        raise business_error(FileNotFoundError, task_id, "Markdown 文件不存在", md_path=md_path_po)

    # 3. 读取正文并回写 state
    md_content: str = md_path_po.read_text(encoding="utf-8")
    state["md_content"] = md_content
    return md_path_po, md_content
```

## D 配置

```python
"""
<服务> 配置.

从 .env 读取连接信息, 装配为全局单例 foo_config.
"""
from dataclasses import dataclass

from app.shared.config.common import env_bool, env_str


@dataclass
class FooConfig:
    """<服务> 配置项."""

    base_url: str      # 服务地址, 例 http://host:port
    api_key: str       # 鉴权 Key
    enabled: bool      # 是否启用


foo_config = FooConfig(
    base_url=env_str("FOO_BASE_URL"),
    api_key=env_str("FOO_API_KEY"),
    enabled=env_bool("FOO_ENABLED"),
)
```

配置只读一次, 业务侧不直接 `os.getenv`.

## E 常量

```python
"""
<领域> 常量.

只定义一次; 名字带单位与领域前缀.
"""
from typing import Final

# 轮询超时, 秒
POLL_TIMEOUT_SECONDS: Final[int] = 600

# 接口路径
BATCH_UPLOAD_PATH: Final[str] = "/file-urls/batch"
```

## F State

```python
from typing import TypedDict


class ImportGraphState(TypedDict):
    """导入流程状态, 字段只增不改名."""

    task_id: str          # 任务 ID
    md_path: str          # md 文件路径
    chunks: list[dict]    # 文本切片
```

## G 测试脚本

```python
"""
<模块> 手动测试.

运行: .venv/Scripts/python -m test.test_xxx
"""
from app.shared.runtime.logger import logger


if __name__ == "__main__":
    logger.info("[提示] 测试开始")
    # 断言真实结果, 不要只 print
    assert True
```

## H 日志与异常速查

```python
logger.debug(f"[调试] task_id={task_id} | 跳过 | file={file_po}")
logger.info(f"[提示] task_id={task_id} | 解析完成 | md_path={md_path}")
logger.warning(f"[警告] task_id={task_id} | 目录已存在, 重建 | dir={dir_po}")
raise business_error(RuntimeError, task_id, "接口返回非 0", code=resp_code)
```

旧日志格式 `task_id(x)【业务终止】-|-原因 field(v)` 全部按上表改写.

## I 提交前 10 条

1. 文件名 函数名 变量名符合 01, 变量带类型后缀.
2. 模块头 3-5 行, 说清职责与边界.
3. 3 步以上有编号, docstring 与代码编号数量一致.
4. 失败统一 `business_error`, 文案只写一次.
5. 日志带 tag 与 task_id, 没有 print.
6. 没有注释代码 无用 import 未使用变量.
7. 常量进 constants, 没有魔法字符串.
8. 节点名来自 `node_constants`, 图与节点文件一致.
9. docstring 里的步骤与代码实际顺序一致.
10. `.venv/Scripts/python -m compileall -q app test` 通过.
