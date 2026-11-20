# 04 日志 log

统一用 `app.shared.runtime.logger`. 业务代码禁止 print 和标准 logging; test 脚本人工核对可用 print.

## 格式

```
[tag] task_id=xxx | 结论 | 字段=值 | 字段=值
```

- tag: 业务日志用 `[调试]` `[提示]` `[警告]` `[终止]` `[异常]`; 装饰器固定输出 `[节点]` `[步骤]`
- 有 task_id 的链路必须带 task_id, 放第一位
- 字段只放排错要用的 1-3 个: 路径 ID 数量 状态码
- 值不加引号, 不换行; 大对象降级 debug 或先截断
- 装饰器的参数与返回值由 `_safe_repr` 自动截断, 不受此限

例:

```python
logger.info(f"[提示] task_id={task_id} | PDF 解析完成 | md_path={md_path}")
logger.warning(f"[警告] task_id={task_id} | 目录已存在, 重建 | dir={dir_po}")
```

校验失败不手写 `logger.error`, 统一用 `business_error`, 它负责记 `[终止]` 并抛异常.

## 级别

| 级别 | 用途 | 例 |
| --- | --- | --- |
| debug | 细节 变量 循环单条 | 跳过不支持的后缀 |
| info | 业务里程碑 外部调用结果 | 解析完成 已入库 N 条 |
| warning | 可恢复 兜底 重试 | 目录已存在, 重建 |
| error | 本次业务失败, 即将抛出 | 接口返回非 0 |
| exception | 仅 except 内, 带堆栈 | 未预期异常 |

## 打点位置

- 入口 出口由装饰器负责, 函数体内不重复写"开始/结束"
- 装饰器把日志位置绑定被装饰函数, 日志里不会出现 wrapper 或框架帧
- 节点: `@node_log(NODE_X)`
- 服务: `@function_log(func_name="中文动作", return_names=["md_path"])`
- 关键分支各一条: 命中或跳过的原因
- 循环内只允许 debug, 每条带元素标识

## 禁止

- 多行拼接日志, emoji, 无字段的"成功了"
- 循环里打 info
- 同一异常不重复写原因: 原因由 `business_error` 记 `[终止]`, 外层只补堆栈
- 打印完整 state 与响应体, 除非 debug 且截断

## 脱敏

`function_log` 已对 password token api_key 等参数打码; 手写日志不要输出密钥.
