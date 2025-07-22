#!/usr/bin/env python3
"""
Тестирование реальных OpenAI API запросов с балансом $10
"""

import asyncio
import sys
import os
sys.path.append('..')

import openai
from src.ai.service import ai_service
from config import Config


async def test_basic_openai_request():
    """Базовый тест OpenAI API"""
    print("🔑 Testing basic OpenAI API request...")

    config = Config()
    if not config.OPENAI_API_KEY:
        print("❌ No OpenAI API key found")
        return False

    try:
        client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello from OpenAI!' in Ukrainian"}
            ],
            max_tokens=50,
            temperature=0.1
        )

        if response.choices and response.choices[0].message.content:
            print(f"✅ OpenAI API Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ Empty response from OpenAI")
            return False

    except openai.AuthenticationError:
        print("❌ Authentication failed - check API key")
        return False
    except openai.RateLimitError:
        print("❌ Rate limit exceeded")
        return False
    except openai.APIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_business_query():
    """Тест бизнес запроса через OpenAI"""
    print("\n💼 Testing business query with OpenAI...")

    config = Config()
    client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Ти помічник компанії з друку та дизайну. Відповідай коротко та по справі на українській мові.
                    Якщо питання про ціни, кажи що це залежить від тиражу та складності, і треба звернутися до менеджера за точним розрахунком."""
                },
                {
                    "role": "user",
                    "content": "Скільки коштують візитки?"
                }
            ],
            max_tokens=200,
            temperature=0.1
        )

        if response.choices and response.choices[0].message.content:
            print(f"✅ Business Query Response:")
            print(f"   {response.choices[0].message.content}")
            return True
        else:
            print("❌ Empty business response")
            return False

    except Exception as e:
        print(f"❌ Business query error: {e}")
        return False


async def test_cost_estimation():
    """Оценка стоимости запросов"""
    print("\n💰 Testing cost estimation...")

    # Примерная стоимость для gpt-4o-mini
    input_cost_per_1k = 0.00015  # $0.15 per 1M tokens
    output_cost_per_1k = 0.0006  # $0.60 per 1M tokens

    # Тестовый запрос
    test_input_tokens = 100  # примерно
    test_output_tokens = 50  # примерно

    cost_per_request = (test_input_tokens * input_cost_per_1k / 1000) + \
        (test_output_tokens * output_cost_per_1k / 1000)

    requests_for_10_dollars = 10 / cost_per_request

    print(f"📊 Cost Analysis:")
    print(f"   • Cost per request: ~${cost_per_request:.6f}")
    print(f"   • Requests possible with $10: ~{requests_for_10_dollars:.0f}")
    print(f"   • Model: gpt-4o-mini (most cost-effective)")


async def test_mock_vs_real_comparison():
    """Сравнение mock и реальных ответов"""
    print("\n🔄 Comparing Mock vs Real AI responses...")

    test_query = "Які терміни виготовлення футболок?"

    # Mock response
    print("🤖 Mock Response:")
    mock_result = await ai_service.process_query(test_query, 12345, 'ukr')
    if mock_result['success']:
        print(f"   {mock_result['answer'][:100]}...")

    # Real OpenAI response
    print("\n🧠 Real OpenAI Response:")
    config = Config()
    try:
        client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Ти помічник компанії з друку та дизайну. Відповідай коротко на українській мові.
                    Для футболок терміни виготовлення зазвичай 2-3 дні, але може варіюватися залежно від тиражу."""
                },
                {
                    "role": "user",
                    "content": test_query
                }
            ],
            max_tokens=150,
            temperature=0.1
        )

        if response.choices and response.choices[0].message.content:
            print(f"   {response.choices[0].message.content}")
        else:
            print("   ❌ No real response received")

    except Exception as e:
        print(f"   ❌ Real API error: {e}")


async def main():
    """Main test function"""
    print("🚀 TESTING REAL OPENAI API")
    print("=" * 50)

    # Test basic API connectivity
    basic_test = await test_basic_openai_request()
    if not basic_test:
        print("\n❌ Basic API test failed. Stopping.")
        return

    # Test business query
    await test_business_query()

    # Cost estimation
    await test_cost_estimation()

    # Mock vs Real comparison
    await test_mock_vs_real_comparison()

    print("\n" + "=" * 50)
    print("🎯 OpenAI API testing complete!")
    print("💡 Ready to integrate real AI into the bot!")


if __name__ == "__main__":
    asyncio.run(main())
