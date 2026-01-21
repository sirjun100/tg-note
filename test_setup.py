#!/usr/bin/env python3
"""
Test script to verify the Intelligent Joplin Librarian setup
Run this after setup to ensure everything is working correctly.
"""

import sys
import os
import importlib

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all required modules can be imported"""
    modules_to_test = [
        'config',
        'src.joplin_client',
        'src.state_manager',
        'src.llm_orchestrator',
        'src.security_utils',
        'src.telegram_orchestrator'
    ]

    print("Testing imports...")
    failed_imports = []

    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append(module)

    if failed_imports:
        print(f"\n❌ {len(failed_imports)} modules failed to import")
        return False
    else:
        print(f"\n✅ All {len(modules_to_test)} modules imported successfully")
        return True

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    try:
        from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ALLOWED_TELEGRAM_USER_IDS

        # Check if required configs are set (they might be None/empty)
        checks = [
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("OPENAI_API_KEY", OPENAI_API_KEY),
            ("ALLOWED_TELEGRAM_USER_IDS", ALLOWED_TELEGRAM_USER_IDS)
        ]

        for name, value in checks:
            if value:
                print(f"✅ {name} is configured")
            else:
                print(f"⚠️  {name} is not set (configure in .env file)")

        print("✅ Configuration module loaded")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_joplin_connection():
    """Test Joplin API connection"""
    print("\nTesting Joplin connection...")
    try:
        from src.joplin_client import JoplinClient

        client = JoplinClient()
        if client.ping():
            print("✅ Joplin API is accessible")
            return True
        else:
            print("⚠️  Joplin API is not accessible (make sure Joplin is running)")
            return False

    except Exception as e:
        print(f"⚠️  Joplin connection test failed: {e}")
        print("   (This is expected if Joplin is not running)")
        return False

def test_llm_providers():
    """Test LLM provider availability"""
    print("\nTesting LLM providers...")
    try:
        from src.llm_providers import registry

        available = registry.get_available_providers()
        if available:
            print(f"✅ {len(available)} LLM provider(s) available: {', '.join(available.keys())}")
            return True
        else:
            print("⚠️  No LLM providers configured")
            print("   Configure OPENAI_API_KEY, OLLAMA_BASE_URL, or DEEPSEEK_API_KEY in .env")
            return False

    except Exception as e:
        print(f"❌ LLM provider test failed: {e}")
        return False

def test_state_manager():
    """Test state manager functionality"""
    print("\nTesting state manager...")
    import tempfile
    import os
    temp_db_path = None

    try:
        from src.state_manager import StateManager

        # Use a temporary file for testing
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        temp_db_path = temp_db.name
        manager = StateManager(temp_db_path)

        # Test basic operations
        test_user_id = 12345
        test_state = {"test": "data"}

        manager.update_state(test_user_id, test_state)
        retrieved = manager.get_state(test_user_id)

        if retrieved == test_state:
            print("✅ State manager basic operations work")
            return True
        else:
            print("❌ State manager data mismatch")
            return False

    except Exception as e:
        print(f"❌ State manager test failed: {e}")
        return False
    finally:
        # Clean up temp file
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.unlink(temp_db_path)
            except:
                pass

def main():
    """Run all tests"""
    print("🧪 Testing Intelligent Joplin Librarian Setup")
    print("=" * 50)

    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("LLM Providers", test_llm_providers),
        ("State Manager", test_state_manager),
        ("Joplin Connection", test_joplin_connection)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("🧪 TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Your setup looks good.")
        print("\nNext: Configure your .env file and run the bot with 'python main.py'")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("   Make sure you've run './setup.sh' and configured your .env file.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)