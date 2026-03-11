#!/usr/bin/env python3
"""
Test LLM providers to ensure they are configured and working
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_llm_providers():
    """Test available LLM providers"""
    from src.llm_orchestrator import LLMOrchestrator
    from src.llm_providers import registry

    print("🧪 Testing LLM Providers")
    print("=" * 40)

    # List all registered providers
    all_providers = registry.list_providers()
    available_providers = registry.get_available_providers()

    print(f"Registered providers: {', '.join(all_providers)}")
    print(f"Available providers: {', '.join(available_providers.keys())}")
    print()

    if not available_providers:
        print("❌ No LLM providers are available!")
        print("Configure at least one provider in your .env file:")
        print("  - OPENAI_API_KEY for OpenAI")
        print("  - OLLAMA_BASE_URL for Ollama (make sure Ollama is running)")
        print("  - DEEPSEEK_API_KEY for DeepSeek")
        return False

    # Test each available provider
    for name, _provider in available_providers.items():
        print(f"Testing {name}...")
        try:
            # Simple test message
            test_message = "Hello, this is a test message for LLM provider validation."

            orchestrator = LLMOrchestrator(provider_name=name)
            result = orchestrator.process_message(test_message)

            if result.status in ["SUCCESS", "NEED_INFO"]:
                print(f"✅ {name} is working")
                provider_info = orchestrator.get_provider_info()
                print(f"   Model: {provider_info['model_name']}")
            else:
                print(f"⚠️  {name} returned unexpected status: {result.status}")

        except Exception as e:
            print(f"❌ {name} failed: {e}")

        print()

    # Test provider switching
    if len(available_providers) > 1:
        print("Testing provider switching...")
        try:
            # Switch to first available provider
            first_provider = list(available_providers.keys())[0]
            orchestrator = LLMOrchestrator(provider_name=first_provider)
            info = orchestrator.get_provider_info()
            print(f"✅ Successfully switched to {info['provider_name']} ({info['model_name']})")
        except Exception as e:
            print(f"❌ Provider switching failed: {e}")

    return len(available_providers) > 0

if __name__ == "__main__":
    success = test_llm_providers()
    if success:
        print("🎉 LLM provider testing completed successfully!")
    else:
        print("❌ LLM provider testing failed!")
        print("Check your configuration and try again.")

    sys.exit(0 if success else 1)
