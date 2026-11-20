"""
提示词加载与渲染测试.

运行: .venv/Scripts/python -m test.test_runtime_load_prompt
"""
from app.shared.runtime.load_prompt import load_prompt


if __name__ == "__main__":
    final_prompt = load_prompt(name="hyde", rewritten_query="参数1")
    assert "参数1" in final_prompt, "占位符未渲染"
    print(final_prompt)
    print("提示词加载测试通过")
