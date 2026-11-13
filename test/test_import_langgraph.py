"""
文档导入 LangGraph 图测试模块。

包含动态执行测试与静态结构打印测试。
动态测试验证状态流转与节点执行链路，静态测试用于可视化图拓扑结构。
"""
from app.process.import_.agent.main_graph import import_graph_app
from app.process.import_.agent.state import ImportGraphState, create_default_state
from app.shared.runtime.logger import logger

# ---------------------------------------------------------------------------
# 动态测试
# ---------------------------------------------------------------------------
# 构造初始状态
state: ImportGraphState = create_default_state(task_id="007", local_file_path="xx.md")

# INFO 级别只记录关键业务标识
logger.info(
    "开始动态执行测试 - task_id: {task_id}, local_file: {file_path}",
    task_id=state.get("task_id"),
    file_path=state.get("local_file_path")
)

# 若需审查全量参数用于排查，降级为 DEBUG 级别。
logger.debug(
    "测试入参全量状态: {state_dict}",
    state_dict=state
)

# 触发图执行
result_state = import_graph_app.invoke(input=state)

# 只提取核心结果字段进行记录，严禁直接打印全量结果对象
logger.info(
    "完成动态执行测试 - task_id: {task_id}, item_name: {item_name}",
    task_id=result_state.get("task_id"),
    item_name=result_state.get("item_name"))

# ---------------------------------------------------------------------------
# 静态测试
# ---------------------------------------------------------------------------
# 打印图的 ASCII 结构，用于验证节点与边的连接关系
import_graph_app.get_graph().print_ascii()
