"""
基础设施配置聚合模块。

将各独立配置文件中的配置实例聚合到统一的 InfraConfig 数据类中，
为上层业务代码提供一站式的全局配置访问入口 infra_config。
"""
# 导入各个独立的基础设施配置实例及其数据类型
from app.shared.config.embedding_config import embedding_config, EmbeddingConfig
from app.shared.config.lm_config import lm_config, LLMConfig
from app.shared.config.bailian_mcp_config import mcp_config, McpConfig
from app.shared.config.milvus_config import milvus_config, MilvusConfig
from app.shared.config.mineru_config import mineru_config, MinerUConfig
from app.shared.config.minio_config import minio_config, MinIOConfig
from app.shared.config.reranker_config import reranker_config, RerankerConfig
from app.shared.config.settings_config import settings, AppSettings
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 配置聚合模型定义
# ---------------------------------------------------------------------------
@dataclass()
class InfraConfig:
    """
    基础设施全局配置聚合类。

    将各个子系统的配置对象组合在一起，方便统一传递与依赖注入。
    使用 field 的 default_factory 延迟加载实例，因为 dataclass 不允许直接
    将可变对象作为默认值。

    Attributes:
       embedding (EmbeddingConfig): 向量模型配置。
       llm (LLMConfig): 大语言模型配置。
       mcp (McpConfig): 联网检索服务配置。
       milvus (MilvusConfig): 向量数据库配置。
       mineru (MinerUConfig): 文档解析服务配置。
       minio (MinIOConfig): 对象存储服务配置。
       reranker (RerankerConfig): 重排模型配置。
       app (AppSettings): 应用基础服务配置。
    """
    embedding: EmbeddingConfig = field(default_factory=lambda: embedding_config)
    llm: LLMConfig = field(default_factory=lambda: lm_config)
    mcp: McpConfig = field(default_factory=lambda: mcp_config)
    milvus: MilvusConfig = field(default_factory=lambda: milvus_config)
    mineru: MinerUConfig = field(default_factory=lambda: mineru_config)
    minio: MinIOConfig = field(default_factory=lambda: minio_config)
    reranker: RerankerConfig = field(default_factory=lambda: reranker_config)
    app: AppSettings = field(default_factory=lambda: settings)


# ---------------------------------------------------------------------------
# 全局实例化
# ---------------------------------------------------------------------------
# 实例化基础设施聚合配置，供全局业务调用。
# 业务侧只需导入 infra_config，即可访问所有子系统的配置项。
infra_config = InfraConfig()
