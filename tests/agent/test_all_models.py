#!/usr/bin/env python3
"""
Test script to verify all available LLM models work with KiroLinter.

This script tests both xAI and Ollama models that are available in your setup.
"""

import os
import sys
from typing import Dict, Any, List

def test_model(model_name: str, provider: str = None) -> Dict[str, Any]:
    """Test a specific model."""
    print(f"\n🔍 Testing {model_name}...")
    
    try:
        from kirolinter.agents.llm_provider import create_llm_provider
        
        # Create provider
        if provider:
            llm = create_llm_provider(provider=provider, model=model_name)
        else:
            llm = create_llm_provider(model=model_name)
        
        # Test connection with a simple prompt
        test_prompt = "Hello! Please respond with 'Test successful' and briefly describe yourself."
        response = llm._call(test_prompt)
        
        print(f"✅ {model_name}: SUCCESS")
        print(f"   Response: {response[:100]}...")
        
        return {
            "model": model_name,
            "success": True,
            "response": response[:200],
            "error": None
        }
        
    except Exception as e:
        print(f"❌ {model_name}: FAILED - {str(e)}")
        return {
            "model": model_name,
            "success": False,
            "response": None,
            "error": str(e)
        }


def test_cli_with_model(model_provider: str) -> Dict[str, Any]:
    """Test CLI with a specific model provider."""
    print(f"\n🚀 Testing CLI with {model_provider}...")
    
    try:
        import subprocess
        
        # Run CLI command
        cmd = [
            sys.executable, "-m", "kirolinter", 
            "agent", "review", 
            "--repo", ".", 
            "--model", model_provider,
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ CLI with {model_provider}: SUCCESS")
            return {"success": True, "output": result.stdout}
        else:
            print(f"❌ CLI with {model_provider}: FAILED")
            print(f"   Error: {result.stderr}")
            return {"success": False, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        print(f"⏰ CLI with {model_provider}: TIMEOUT")
        return {"success": False, "error": "Timeout after 60 seconds"}
    except Exception as e:
        print(f"❌ CLI with {model_provider}: ERROR - {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """Run comprehensive model tests."""
    print("🚀 Testing All Available Models for KiroLinter")
    print("=" * 50)
    
    # Test results storage
    results = {
        "xai_models": [],
        "ollama_models": [],
        "cli_tests": []
    }
    
    # Test xAI models (only grok-3-mini to avoid costs)
    print("\n📡 Testing xAI Models...")
    xai_models = ["xai/grok-3-mini"]
    
    for model in xai_models:
        result = test_model(model, "xai")
        results["xai_models"].append(result)
    
    # Test Ollama models (gemma, llama, qwen)
    print("\n🏠 Testing Ollama Models...")
    ollama_models = [
        "ollama/gemma3n:e4b",     # Gemma model
        "ollama/llama3.1:8b",     # Llama model  
        "ollama/qwen3:8b"         # Qwen model
    ]
    
    for model in ollama_models:
        result = test_model(model)
        results["ollama_models"].append(result)
    
    # Test CLI integration
    print("\n🖥️  Testing CLI Integration...")
    cli_providers = ["xai", "ollama", "auto"]
    
    for provider in cli_providers:
        result = test_cli_with_model(provider)
        results["cli_tests"].append({"provider": provider, **result})
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    # xAI Results
    xai_success = sum(1 for r in results["xai_models"] if r["success"])
    print(f"🤖 xAI Models: {xai_success}/{len(results['xai_models'])} successful")
    for result in results["xai_models"]:
        status = "✅" if result["success"] else "❌"
        print(f"   {status} {result['model']}")
    
    # Ollama Results  
    ollama_success = sum(1 for r in results["ollama_models"] if r["success"])
    print(f"🏠 Ollama Models: {ollama_success}/{len(results['ollama_models'])} successful")
    for result in results["ollama_models"]:
        status = "✅" if result["success"] else "❌"
        print(f"   {status} {result['model']}")
    
    # CLI Results
    cli_success = sum(1 for r in results["cli_tests"] if r["success"])
    print(f"🖥️  CLI Tests: {cli_success}/{len(results['cli_tests'])} successful")
    for result in results["cli_tests"]:
        status = "✅" if result["success"] else "❌"
        print(f"   {status} {result['provider']}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    # Find best xAI model
    working_xai = [r for r in results["xai_models"] if r["success"]]
    if working_xai:
        best_xai = working_xai[0]["model"]  # First working one
        print(f"🚀 For xAI: Use {best_xai}")
    
    # Find best Ollama model
    working_ollama = [r for r in results["ollama_models"] if r["success"]]
    if working_ollama:
        best_ollama = working_ollama[0]["model"]  # First working one
        print(f"🏠 For Ollama: Use {best_ollama}")
    
    # Usage examples
    print(f"\n🎯 USAGE EXAMPLES:")
    if working_xai:
        print(f"   python -m kirolinter agent review --repo . --model xai --verbose")
    if working_ollama:
        print(f"   python -m kirolinter agent review --repo . --model ollama --verbose")
    
    print(f"\n🏁 Testing completed!")
    
    # Return overall success
    total_success = xai_success + ollama_success + cli_success
    total_tests = len(results["xai_models"]) + len(results["ollama_models"]) + len(results["cli_tests"])
    
    if total_success > 0:
        print(f"🎉 {total_success}/{total_tests} tests passed - LiteLLM integration is working!")
        return 0
    else:
        print(f"😞 No tests passed - please check your configuration")
        return 1


if __name__ == "__main__":
    sys.exit(main())