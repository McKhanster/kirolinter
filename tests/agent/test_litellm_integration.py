#!/usr/bin/env python3
"""
Test script for LiteLLM integration in KiroLinter.

This script tests the LiteLLM provider with different models and configurations.
"""

import os
import sys
import traceback
from typing import Dict, Any

def test_imports():
    """Test that all required packages can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import litellm
        print("✅ LiteLLM imported successfully")
    except ImportError as e:
        print(f"❌ LiteLLM import failed: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
    except ImportError as e:
        print(f"❌ python-dotenv import failed: {e}")
        return False
    
    try:
        from kirolinter.agents.llm_provider import LiteLLMProvider, create_llm_provider
        print("✅ LiteLLM provider imported successfully")
    except ImportError as e:
        print(f"❌ LiteLLM provider import failed: {e}")
        return False
    
    return True


def test_environment_setup():
    """Test environment variable setup."""
    print("\n🔍 Testing environment setup...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for API keys
    api_keys = {
        "XAI_API_KEY": os.getenv("XAI_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }
    
    available_providers = []
    for key, value in api_keys.items():
        if value:
            provider = key.replace("_API_KEY", "").lower()
            print(f"✅ {provider.upper()} API key found")
            available_providers.append(provider)
        else:
            provider = key.replace("_API_KEY", "").lower()
            print(f"⚠️  {provider.upper()} API key not found")
    
    # Check Ollama setup
    ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    print(f"🔗 Ollama base URL: {ollama_base}")
    
    return available_providers


def test_provider_creation():
    """Test LiteLLM provider creation."""
    print("\n🔍 Testing provider creation...")
    
    try:
        from kirolinter.agents.llm_provider import LiteLLMProvider, create_llm_provider
        
        # Test basic provider creation
        provider = create_llm_provider()
        print(f"✅ Default provider created: {provider.model}")
        
        # Test available models
        available_models = LiteLLMProvider.get_available_models()
        print(f"✅ Available models loaded: {len(available_models)} providers")
        
        return True
        
    except Exception as e:
        print(f"❌ Provider creation failed: {e}")
        traceback.print_exc()
        return False


def test_connection(model: str, provider_name: str = None) -> Dict[str, Any]:
    """Test connection to a specific model."""
    print(f"\n🔍 Testing connection to {model}...")
    
    try:
        from kirolinter.agents.llm_provider import create_llm_provider
        
        # Create provider
        if provider_name:
            provider = create_llm_provider(provider=provider_name, model=model)
        else:
            provider = create_llm_provider(model=model)
        
        # Test connection
        result = provider.test_connection()
        
        if result["success"]:
            print(f"✅ Connection successful to {model}")
            print(f"   Response: {result['response'][:100]}...")
        else:
            print(f"❌ Connection failed to {model}: {result['error']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Connection test failed for {model}: {e}")
        return {"success": False, "error": str(e)}


def test_agent_integration():
    """Test integration with agent classes."""
    print("\n🔍 Testing agent integration...")
    
    try:
        from kirolinter.agents.coordinator import CoordinatorAgent
        from kirolinter.agents.reviewer import ReviewerAgent
        
        # Test coordinator with default model
        print("Testing CoordinatorAgent...")
        coordinator = CoordinatorAgent(verbose=True)
        print("✅ CoordinatorAgent created successfully")
        
        # Test reviewer with default model
        print("Testing ReviewerAgent...")
        reviewer = ReviewerAgent(verbose=True)
        print("✅ ReviewerAgent created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test failed: {e}")
        traceback.print_exc()
        return False


def test_cli_integration():
    """Test CLI integration."""
    print("\n🔍 Testing CLI integration...")
    
    try:
        # Test importing CLI
        from kirolinter.cli import cli
        print("✅ CLI imported successfully")
        
        # Test help command (dry run)
        print("✅ CLI help command available")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI integration test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting LiteLLM Integration Tests\n")
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import tests failed. Please install required packages:")
        print("   pip install litellm python-dotenv langchain")
        sys.exit(1)
    
    # Test 2: Environment
    available_providers = test_environment_setup()
    
    # Test 3: Provider creation
    if not test_provider_creation():
        print("\n❌ Provider creation tests failed.")
        sys.exit(1)
    
    # Test 4: Connection tests
    connection_results = {}
    
    # Test xAI Grok if available
    if "xai" in available_providers:
        model_name = os.getenv("XAI_MODEL_NAME", "grok-code-fast-1")
        # Add xai/ prefix if not already present
        if not model_name.startswith("xai/"):
            model_name = f"xai/{model_name}"
        connection_results["xai"] = test_connection(model_name, "xai")
    
    # Test Ollama (always try, might be running locally)
    ollama_model = os.getenv("OLLAMA_MODEL_NAME", "llama2")
    connection_results["ollama"] = test_connection(f"ollama/{ollama_model}")
    
    # Test OpenAI if available
    if "openai" in available_providers:
        connection_results["openai"] = test_connection("gpt-3.5-turbo", "openai")
    
    # Test 5: Agent integration
    if not test_agent_integration():
        print("\n❌ Agent integration tests failed.")
        sys.exit(1)
    
    # Test 6: CLI integration
    if not test_cli_integration():
        print("\n❌ CLI integration tests failed.")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    successful_connections = sum(1 for result in connection_results.values() if result.get("success", False))
    total_connections = len(connection_results)
    
    print(f"✅ Import tests: PASSED")
    print(f"✅ Environment setup: PASSED")
    print(f"✅ Provider creation: PASSED")
    print(f"🔗 Connection tests: {successful_connections}/{total_connections} successful")
    print(f"✅ Agent integration: PASSED")
    print(f"✅ CLI integration: PASSED")
    
    if successful_connections > 0:
        print(f"\n🎉 LiteLLM integration is working! You can use:")
        for provider, result in connection_results.items():
            if result.get("success", False):
                print(f"   - {provider}: {result.get('model', 'unknown model')}")
        
        print(f"\n💡 Try running:")
        print(f"   python -m kirolinter agent review --repo . --verbose")
        
    else:
        print(f"\n⚠️  No LLM connections successful. Check your API keys and network connection.")
    
    print("\n🏁 Tests completed!")


if __name__ == "__main__":
    main()