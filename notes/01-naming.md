# 01 命名 naming

原则: 见名知意. 宁可长一点, 不要 a b tmp data.
读法: 范围_主体_类型, 例 output_mineru_zip_dir_po.

## 包 文件

- 全小写加下划线: `entry_service.py`
- 与关键字冲突时加尾下划线: `import_`, import 是关键字
- 后缀定角色: `*_service.py` 业务, `node_*.py` 图节点, `*_config.py` 配置, `*_constants.py` 常量, `*_utils.py` 工具
- 一个文件一个主题, 文件名与主函数对应: `pdf_parse_service.py` -> `parse_pdf_to_markdown`
- `__init__.py` 留空, 不做重导出

## 类

- 大驼峰: `ImportGraphState`
- 后缀定角色: Config State Provider Event
- 数据类字段用小写下划线, 与 `.env` 变量一一对应

## 函数

- 动词开头, 小写下划线: `resolve_input_file`
- 动词只用这些: get 读内存或配置, load 读文件, request 调接口, parse 解析, validate 校验, build 组装, poll 轮询, upload download 传文件, scan 扫描, summarize 生成摘要, enrich 补全, index 入库, split 切分, push 推送, clear 清理, ensure 兜底初始化
- 不用第三人称: `validate_pdf_paths`, 不写 `validates_pdf_paths`
- 布尔函数用 `is_` `has_` `can_` 前缀
- 内部函数加下划线前缀: `_ensure_task`
- 装饰器按用途命名: `node_log` `function_log` `step_log`

## 变量

类型后缀是硬约定:

| 后缀 | 含义 | 例 |
| --- | --- | --- |
| _po | pathlib.Path 对象 | pdf_path_po |
| _path | str 路径 | md_path |
| _url | str 链接 | upload_url |
| _list | list | md_file_list |
| _map | dict | image_desc_map |
| _seconds | 秒 | POLL_TIMEOUT_SECONDS |
| _ms | 毫秒 | cost_ms |
| _id | 标识 | task_id batch_id |
| _name | 名称 | image_name |
| _stem | 去后缀文件名 | pdf_stem |
| is_ | bool | is_md_read_enabled |

- 时间: `start_ts` 起点, `elapsed_s` 已用秒数, `cost_ms` 耗时毫秒
- 请求: `request_url` `request_headers` `request_payload`
- 响应: `resp` `resp_data` `status_code` `resp_code`
- 循环: 用真实名词, 如 `md_file_po`; 只有纯下标才用 i j
- 不超过 5 段; 缩写白名单: id url path md pdf img api http json llm vl rag zip kb min max

## 常量

- 全大写加下划线, 领域前缀: `MINERU_` `JSON_KEY_` `HTTP_STATUS_` `PROMPT_` `LOG_` `NODE_`
- 单位进名字: `POLL_TIMEOUT_SECONDS`, 不写 `POLL_TIMEOUT`
- 多处使用的字符串与数字必须进 constants
- 名字与值同名时不要加词: `PROMPT_HYDE = "hyde"`

## 禁止

- data info tmp temp obj res r a1
- 拼音与中文标识符
- 同物异名: 同一概念只用一个词, 统一用 state image chunk
- 否定式布尔: 用 `is_disabled`, 不用 `is_not_enabled`
