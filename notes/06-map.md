# 06 项目地图 map

## 扫描范围

先读 `.gitignore`, 过滤忽略路径, 再扫描源码与配置.

参与分析:

- `app/**/*.py` 40 个非空文件
- `test/**/*.py` 5 个手动脚本
- `app/resources/prompts/*.prompt` 7 个提示词
- `pyproject.toml` `.env.example` `README.md`

被过滤:

| 规则 | 内容 |
| --- | --- |
| `.venv/` `.idea/` `.git/` | 虚拟环境与工具 |
| `__pycache__/` `*.py[codz]` | 字节码与缓存 |
| `logs/` `output/` `doc/` | 本地产物与输入文档 |
| `build/` `dist/` `*.egg-info/` | 构建产物 |
| `.env` `.pypirc` | 密钥 |
| `models/` | 空目录, 无源码 |

`notes/` 原在忽略列表中, 规范需要两人共享, 已从 `.gitignore` 移除.

## 目录

```
app/
  api/                     空, 预留 FastAPI 入口
  constants/               file http mineru node prompt
  infra/                   config 聚合, llm provider, minio 网关
  process/import_/agent/   主图 状态 7 个节点
  rag/import_/             导入服务 7 个
  shared/                  config logger error load_prompt sse task, clients minio
  resources/prompts/       7 个提示词
test/                      5 个手动测试
```

## 导入数据流

```
node_entry
  ├─ md  -> node_md_img
  └─ pdf -> node_pdf_to_md -> node_md_img
node_md_img -> node_document_split -> node_item_name_recognition
            -> node_bge_embedding -> node_import_milvus -> END
```

## 关键文件

| 文件 | 职责 |
| --- | --- |
| process/import_/agent/main_graph.py | 建图 边 条件路由 |
| process/import_/agent/state.py | ImportGraphState 与默认状态 |
| process/import_/agent/nodes/*.py | 7 个节点, 固定三步 |
| rag/import_/entry_service.py | 入口路径校验与类型识别 |
| rag/import_/pdf_parse_service.py | MinerU 申请 上传 轮询 下载 解压 |
| rag/import_/enrich_markdown_images.py | 扫描 摘要 上传 MinIO 替换地址, 已实现 |
| rag/import_/split_document.py | 切分, stub |
| rag/import_/item_name_service.py | 主体识别, stub |
| rag/import_/embedding_service.py | BGE-M3 向量化, stub |
| rag/import_/index_service.py | Milvus 入库, stub |
| infra/minio/minio_gateway.py | 桶名 图片前缀 客户端 图片 URL |
| shared/clients/minio_utils.py | MinIO 客户端懒加载与桶初始化 |
| shared/runtime/logger.py | logger 与 node_log function_log |
| shared/runtime/error_utils.py | business_error 统一失败 |
| shared/utils/sse_utils.py | SSE 队列与生成器 |
| shared/utils/task_utils.py | 任务进度 与中文节点名映射 |
| shared/config/common.py | .env 读取与类型转换 |
| infra/config/providers.py | infra_config 配置聚合 |
| constants/node_constants.py | 节点名唯一来源 |

## 加一个节点

1. `constants/node_constants.py` 加 `NODE_X`.
2. `nodes/node_x.py` 复制模板 05-B, 用 `NODE_X`.
3. `main_graph.py` 注册节点与边.
4. `task_utils.py` 的中文名映射加一行.
5. 跑 `.venv/Scripts/python -m test.test_import_langgraph`.

## 未实现

- 切分 主体识别 向量化 入库 四个服务
- `app/api` 无路由, 查询流程未建
- `.env.example` 里的 MONGO_* 暂无代码使用
- MinIO 上传未连真实服务联调

## 图片对象

- 对象键: `{image_prefix}/{md_stem}/{image_name}`, 前缀来自 `MINIO_IMG_DIR` 去首尾斜杠
- 访问 URL: `http(s)://{endpoint}/{bucket}/{对象键}`
- 写入顺序: 先上传, 全部成功后才删除本次未引用的旧对象
