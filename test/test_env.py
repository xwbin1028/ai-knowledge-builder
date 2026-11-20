"""
环境变量加载测试.

运行: .venv/Scripts/python -m test.test_env
"""
from app.shared.config.common import env_str


if __name__ == "__main__":
    app_env = env_str("APP_ENV")
    print(f"APP_ENV={app_env}")
    assert app_env, ".env 未加载或缺少 APP_ENV"
    print("环境变量测试通过")
