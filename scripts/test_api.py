"""
API 测试脚本
用法: python scripts/test_api.py
直接从原 test_api.py 提取
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from config.settings import CLIENT_CONFIG


def test_api():
    print("=" * 50)
    print("🔧 API 连接测试")
    print("=" * 50)
    print(f"Base URL: {CLIENT_CONFIG['base_url']}")
    print(f"Model: {CLIENT_CONFIG['model']}")
    print(f"API Key: {CLIENT_CONFIG['api_key'][:10]}...{CLIENT_CONFIG['api_key'][-5:]}")
    print("=" * 50)
    
    try:
        # 初始化客户端
        client = OpenAI(
            api_key=CLIENT_CONFIG['api_key'],
            base_url=CLIENT_CONFIG['base_url']
        )
        
        print("\n📤 发送测试请求...")
        
        # 发送简单请求
        response = client.chat.completions.create(
            model=CLIENT_CONFIG['model'],
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
