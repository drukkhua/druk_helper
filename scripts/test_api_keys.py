#!/usr/bin/env python3
"""
Script to test OpenAI API keys and find a working one
"""

import asyncio
import openai
import os
from typing import List, Optional


async def test_api_key(api_key: str) -> bool:
    """Test if an API key is valid by making a simple request"""
    try:
        client = openai.AsyncOpenAI(api_key=api_key)

        # Simple test request
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5,
            temperature=0,
        )

        if response.choices and response.choices[0].message.content:
            print(f"✅ API Key working: {api_key[:15]}...")
            return True

    except openai.AuthenticationError:
        print(f"❌ Authentication failed: {api_key[:15]}...")
    except openai.RateLimitError:
        print(f"⚠️  Rate limit exceeded: {api_key[:15]}...")
    except openai.APIError as e:
        print(f"❌ API Error: {api_key[:15]}... - {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {api_key[:15]}... - {str(e)}")

    return False


async def find_working_api_key() -> Optional[str]:
    """Find the first working API key from the list"""
    # Read API keys from file
    try:
        with open("OPEN-API.txt", "r") as f:
            api_keys = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ OPEN-API.txt file not found")
        return None

    print(f"Testing {len(api_keys)} API keys...")

    for i, api_key in enumerate(api_keys, 1):
        print(f"\n[{i}/{len(api_keys)}] Testing API key: {api_key[:15]}...")

        if await test_api_key(api_key):
            print(f"\n🎉 Found working API key: {api_key[:15]}...")
            return api_key

    print("\n❌ No working API keys found")
    return None


async def test_with_real_query(api_key: str) -> None:
    """Test the API key with a real business query"""
    try:
        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник полиграфической компании. Отвечай кратко и по делу на украинском языке.",
                },
                {"role": "user", "content": "Скільки коштують візитки?"},
            ],
            max_tokens=150,
            temperature=0.1,
        )

        if response.choices and response.choices[0].message.content:
            print(f"\n🎯 Real query test successful:")
            print(f"Answer: {response.choices[0].message.content}")
            return True

    except Exception as e:
        print(f"❌ Real query test failed: {str(e)}")
        return False


async def main():
    """Main test function"""
    print("🔍 Starting OpenAI API key testing...\n")

    # Find working API key
    working_key = await find_working_api_key()

    if working_key:
        # Test with real query
        print(f"\n🧪 Testing real query with key: {working_key[:15]}...")
        await test_with_real_query(working_key)

        # Update .env file
        print(f"\n📝 Updating .env file with working key...")

        # Read current .env
        with open(".env", "r") as f:
            env_content = f.read()

        # Update the API key line
        lines = env_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("OPENAI_API_KEY="):
                lines[i] = f"OPENAI_API_KEY={working_key}"
                break

        # Write back to .env
        with open(".env", "w") as f:
            f.write("\n".join(lines))

        print(f"✅ .env file updated with working API key!")

    else:
        print("❌ No working API keys found. Using mock responses only.")


if __name__ == "__main__":
    asyncio.run(main())
