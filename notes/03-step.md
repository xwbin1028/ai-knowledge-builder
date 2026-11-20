# 03 步骤 step

目标: 任意函数 30 秒内看懂顺序与失败点.

## 粒度

- 1 步 = 1 个动作 + 1 个产物, 产物写进步骤: `2. 校验路径, 得到 pdf_path_po`
- 一个函数 3-7 步; 超过 7 步拆函数; 少于 3 步不编号
- 嵌套不超过 2 层, 提前 return 代替 else
- 一个函数只做一件事, 步骤名里不出现"并且"

## 固定顺序

1. 取参: 从 state 或入参取值, 校验类型与空值
2. 转换: str 转 Path, dict 转模型
3. IO: 请求 读写 模型调用
4. 校验结果: 状态码 字段 存在性
5. 回写: 集中写回 state, 不散落
6. 返回: 单返回值优先, 多返回值不超过 3 个

- 持久事实写 state; `batch_id` `upload_url` `zip_url` 等协议瞬时值用参数与返回值, 不塞 state

## 写法

docstring 与代码编号必须一一对应:

```
业务逻辑:
    1. 取 pdf_path 与 local_file_dir
    2. 校验并转 Path
    3. 申请上传链接

# 1. 取 pdf_path 与 local_file_dir
...
# 2. 校验并转 Path
...
```

- 编号连续, 数量一致, 顺序一致; 改代码必须同步改 docstring
- 步骤标题用"动词 + 对象", 不写"进行 处理 相关"
- 代码区块之间空一行

## 失败处理

- 校验失败: `raise business_error(ValueError, task_id, "原因", 字段=值)`
- 外部调用: 先判 HTTP 状态码, 再判业务码, 不对就抛
- 可恢复: 记 warning 后 continue 或重试; 不可恢复: 立即终止
- 不吞异常, 不用 return None 表示失败
- 待实现接口抛 `NotImplementedError`, 属于开发期占位, 不算业务失败
- 文案只写一次, 由 `business_error` 同时打日志和构造异常

## 节点函数

固定三步, 不写编号注释:

```
add_running_task(state["task_id"], NODE_X)
state = 服务函数(state)
add_done_task(state["task_id"], NODE_X)
```

## 拆分信号

- 出现 2 个以上 IO
- 参数超过 5 个
- docstring 超过 25 行
- 步骤里出现"并且"
