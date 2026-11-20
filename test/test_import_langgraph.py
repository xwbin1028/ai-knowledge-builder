"""
导入流程结构测试.

运行: .venv/Scripts/python -m test.test_import_langgraph
设置 IMPORT_TEST_FILE 后可跑真实文件联调.
"""
import os

from app.process.import_.agent.main_graph import import_graph_app
from app.process.import_.agent.state import create_default_state
from app.shared.runtime.logger import logger


if __name__ == "__main__":
    # 1. 打印图结构, 校验节点与边
    import_graph_app.get_graph().print_ascii()

    # 2. 设置 IMPORT_TEST_FILE 时跑真实文件
    test_file = os.getenv("IMPORT_TEST_FILE", "")
    if not test_file:
        logger.info("[提示] 未设置 IMPORT_TEST_FILE, 只检查图结构")
    else:
        state = create_default_state(task_id="test_import_001", local_file_path=test_file)
        result_state = import_graph_app.invoke(input=state)
        logger.info(
            f"[提示] 联调完成 | task_id={result_state.get('task_id')} "
            f"| md_path={result_state.get('md_path')}"
        )
