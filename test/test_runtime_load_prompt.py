"""
提示词加载与渲染工具测试模块。

该模块用于验证 app.shared.runtime.load_prompt
是否能正确读取项目资源目录下的 .prompt 文件，并根据传入的关键字参数
成功渲染占位符。

当前测试用例：验证 /app/resources/prompts/hyde_prompt.prompt 模板的渲染。
"""
from app.shared.runtime.load_prompt import load_prompt

# ---------------------------------------------------------------------------
# 提示词功能测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 调用渲染方法，传入模板名称与对应的变量
    # 注意：kwargs 的键名 rewritten_query 必须与 hyde_prompt.prompt 文件中的占位符完全一致
    final_prompt = load_prompt(
        name="hyde_prompt",
        rewritten_query="参数1"
    )

    # 打印渲染后的最终结果，用于人工核对占位符是否被正确替换
    print("✅ 渲染后的最终提示词：")
    print(final_prompt)
