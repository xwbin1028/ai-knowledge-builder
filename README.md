# ai-knowledge-builder

企业文档 RAG 导入流水线: PDF 或 Markdown -> MinerU 解析 -> 图片增强 -> 切分 -> 向量化 -> Milvus.

## 目录

- `app/process/import_`: LangGraph 编排与节点
- `app/rag/import_`: 导入侧服务
- `app/shared`: 日志 配置 SSE 任务追踪
- `app/infra`: 配置聚合, 模型 provider 与 MinIO 网关
- `notes/`: 编码规范, 先读 notes/README.md
- `test/`: 手动测试脚本

## 运行

```powershell
uv sync
.venv/Scripts/python -m test.test_import_langgraph
```
