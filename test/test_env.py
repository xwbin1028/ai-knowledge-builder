"""
环境变量加载测试模块。

该模块专门用于验证项目根目录下的 .env 文件是否被正确加载，
以及对应的环境变量(如 APP_ENV)是否能被系统成功读取。
"""
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 环境变量测试
# ---------------------------------------------------------------------------

# 加载项目根目录的 .env 文件
# override=True 表示如果系统中已存在同名环境变量，则强制使用 .env 文件中的值覆盖
load_dotenv(override=True)

if __name__ == "__main__":
    # 读取并打印当前的环境标识，验证 .env 是否成功加载
    app_env = os.environ.get("APP_ENV")

    print(f"当前环境标识 (APP_ENV): {app_env}")

    if app_env is None:
        print("警告：未能读取到 APP_ENV，请检查 .env 文件是否存在或路径是否正确。")
    else:
        print("环境变量加载测试通过！")
