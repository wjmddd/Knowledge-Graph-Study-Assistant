"""
简单的 API 测试脚本
用于验证 API Key 是否可用
"""

from openai import OpenAI

# === 配置 (与 pipeline.py 保持一致) ===
API_KEY = "sk-pGezF366dyAXhRktmeRXkWs4XEQ8h5TH8xUb9vyDl2pSFP0I"
BASE_URL = "https://sg.uiuiapi.com/v1"
MODEL = "qwen3-30b-a3b-instruct-2507"

def test_api():
    print("=" * 50)
    print("🔧 API 连接测试")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print("=" * 50)
    
    try:
        # 初始化客户端
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        print("\n📤 发送测试请求...")
        
        # 发送简单请求
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "请用一句话介绍什么是CPU。"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        # 获取回复
        reply = response.choices[0].message.content
        
        print("\n✅ API 连接成功!")
        print(f"\n📥 模型回复:\n{reply}")
        print("\n" + "=" * 50)
        print("🎉 测试通过! API Key 可用。")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ API 连接失败!")
        print(f"错误信息: {e}")
        print("\n可能的原因:")
        print("1. API Key 无效或过期")
        print("2. Base URL 不正确")
        print("3. 模型名称错误")
        print("4. 网络连接问题")
        print("5. 账户余额不足")
        return False

if __name__ == "__main__":
    test_api()

