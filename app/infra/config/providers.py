"""
基础设施配置聚合.

把各子系统配置汇总为 infra_config, 业务侧只导入这一个入口.
"""
from dataclasses import dataclass, field

from app.shared.config.bailian_mcp_config import McpConfig, mcp_config
from app.shared.config.embedding_config import EmbeddingConfig, embedding_config
from app.shared.config.lm_config import LLMConfig, lm_config
from app.shared.config.milvus_config import MilvusConfig, milvus_config
from app.shared.config.mineru_config import MinerUConfig, mineru_config
from app.shared.config.minio_config import MinIOConfig, minio_config
from app.shared.config.reranker_config import RerankerConfig, reranker_config
from app.shared.config.settings_config import AppSettings, settings


@dataclass
class InfraConfig:
    """基础设施配置汇总."""

    embedding: EmbeddingConfig = field(default_factory=lambda: embedding_config)
    llm: LLMConfig = field(default_factory=lambda: lm_config)
    mcp: McpConfig = field(default_factory=lambda: mcp_config)
    milvus: MilvusConfig = field(default_factory=lambda: milvus_config)
    mineru: MinerUConfig = field(default_factory=lambda: mineru_config)
    minio: MinIOConfig = field(default_factory=lambda: minio_config)
    reranker: RerankerConfig = field(default_factory=lambda: reranker_config)
    app: AppSettings = field(default_factory=lambda: settings)


infra_config = InfraConfig()
