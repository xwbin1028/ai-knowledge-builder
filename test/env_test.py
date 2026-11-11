from dotenv import load_dotenv
import os

# 向上递归查找项目 .env 环境变量
# override=True 如果系统中已存在同名环境变量
# 则用 .env 文件中的值覆盖它
load_dotenv(override=True)

print(os.environ.get("APP_ENV"))
