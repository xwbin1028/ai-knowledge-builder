"""
基础设施配置聚合测试模块。

该模块用于验证 app.infra.config.providers 中的 infra_config 全局单例
是否成功装配，并测试底层环境变量是否被正确读取和传递。
"""
from app.infra.config.providers import infra_config


# ---------------------------------------------------------------------------
# 门面测试
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # 打印导入服务的应用名称。
    print(infra_config.app.import_app_name)
