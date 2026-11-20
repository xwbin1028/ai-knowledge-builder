"""
MinIO 网关.

统一提供桶名 图片前缀 客户端与图片访问 URL, 业务侧不直接读配置或拼对象键.
"""
from minio import Minio

from app.infra.config.providers import infra_config
from app.shared.clients.minio_utils import get_minio_client


class MinIOGateway:
    """MinIO 配置与访问入口, 全局单例 minio_gateway."""

    @property
    def bucket_name(self) -> str:
        """桶名."""
        return infra_config.minio.bucket_name

    @property
    def image_dir(self) -> str:
        """配置中的图片目录, 形如 /kb-images."""
        return infra_config.minio.minio_img_dir

    @property
    def image_prefix(self) -> str:
        """对象键前缀, 去掉首尾斜杠, 形如 kb-images."""
        return self.image_dir.strip("/")

    @property
    def client(self) -> Minio:
        """全局 MinIO 客户端."""
        return get_minio_client()

    def object_name(self, md_stem: str, image_name: str) -> str:
        """
        拼接图片对象键.

        Args:
            md_stem: 文档主文件名.
            image_name: 图片文件名.

        Returns:
            str: 形如 kb-images/doc/a.jpg.
        """
        parts = [part for part in (self.image_prefix, md_stem, image_name) if part]
        return "/".join(parts)

    def prefix_for(self, md_stem: str) -> str:
        """
        拼接某文档的图片对象前缀, 末尾带斜杠.

        Args:
            md_stem: 文档主文件名.

        Returns:
            str: 形如 kb-images/doc/.
        """
        prefix = f"{self.image_prefix}/{md_stem}" if self.image_prefix else md_stem
        return f"{prefix}/"

    def build_image_url(self, md_stem: str, image_name: str) -> str:
        """
        生成图片访问 URL.

        Args:
            md_stem: 文档主文件名.
            image_name: 图片文件名.

        Returns:
            str: http(s)://endpoint/bucket/prefix/stem/image.
        """
        protocol = "https" if infra_config.minio.minio_secure else "http"
        endpoint = infra_config.minio.endpoint.rstrip("/")
        bucket = self.bucket_name
        object_name = self.object_name(md_stem, image_name)
        return f"{protocol}://{endpoint}/{bucket}/{object_name}"


# 全局唯一网关, 全项目复用
minio_gateway = MinIOGateway()
