"""
基础设施配置聚合测试.

运行: .venv/Scripts/python -m test.test_config_infra
"""
from app.infra.config.providers import infra_config


if __name__ == "__main__":
    assert infra_config.app.import_app_name, "缺少 import_app_name"
    assert infra_config.llm.base_url is not None, "缺少 llm.base_url"
    print(f"import_app_name={infra_config.app.import_app_name}")
    print("基础设施配置测试通过")
