"""
LiteLLM configuration for KiroLinter AI Agent System.

This module provides flexible LLM configuration supporting:
- xAI Grok models
- Local models via Ollama
- OpenAI models (fallback)
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

try:
    import litellm
    from langchain_community.llms import LiteLLM
    from langchain_community.chat_models import ChatLiteLLM
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Load environment variables
load_dotenv()


class LLMConfig:
    """Configuration manager for LiteLLM integration."""
    
    def __init__(self):
        """Initialize LLM configuration."""
        self.xai_api_key = os.getenv("XAI_API_KEY")
        self.xai_model = os.getenv("XAI_MODEL_NAME", "grok-3-mini")
        self.ollama_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL_NAME", "gemma3n:e4b")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Default model preference order
        self.model_preference = [
            "xai",      # xAI Grok (if API key available)
            "ollama",   # Local Ollama (if running)
            "openai"    # OpenAI (fallback)
        ]
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get available model configurations."""
        models = {}
        
        # xAI Grok configuration
        if self.xai_api_key:
            models["xai"] = {
                "model": f"xai/{self.xai_model}",
                "api_key": self.xai_api_key,
                "temperature": 0.1,
                "max_tokens": 4000,
                "description": f"xAI {self.xai_model}"
            }
        
        # Ollama configuration
        if self._is_ollama_available():
            models["ollama"] = {
                "model": f"ollama/{self.ollama_model}",
                "api_base": self.ollama_base,
                "temperature": 0.1,
                "max_tokens": 4000,
                "description": f"Ollama {self.ollama_model}"
            }
        
        # OpenAI configuration (fallback)
        if self.openai_api_key:
            models["openai"] = {
                "model": "gpt-4",
                "api_key": self.openai_api_key,
                "temperature": 0.1,
                "max_tokens": 4000,
                "description": "OpenAI GPT-4"
            }
        
        return models
    
    def get_preferred_model(self) -> Optional[Dict[str, Any]]:
        """Get the preferred available model based on preference order."""
        available_models = self.get_available_models()
        
        for provider in self.model_preference:
            if provider in available_models:
                config = available_models[provider].copy()
                config["provider"] = provider
                return config
        
        return None
    
    def create_chat_model(self, provider: Optional[str] = None, **kwargs) -> Any:
        """
        Create a chat model instance.
        
        Args:
            provider: Specific provider to use (xai, ollama, openai)
            **kwargs: Additional model parameters
            
        Returns:
            Chat model instance
        """
        if not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM not available. Install with: pip install litellm")
        
        available_models = self.get_available_models()
        
        if provider and provider in available_models:
            config = available_models[provider]
        else:
            config = self.get_preferred_model()
            if not config:
                raise ValueError("No LLM providers available. Check your API keys and configuration.")
        
        # Merge kwargs with config
        model_config = config.copy()
        model_config.update(kwargs)
        
        try:
            # Create LiteLLM chat model
            chat_model = ChatLiteLLM(
                model=model_config["model"],
                temperature=model_config.get("temperature", 0.1),
                max_tokens=model_config.get("max_tokens", 4000),
                api_key=model_config.get("api_key"),
                api_base=model_config.get("api_base"),
                **{k: v for k, v in model_config.items() 
                   if k not in ["model", "temperature", "max_tokens", "api_key", "api_base", "provider", "description"]}
            )
            
            return chat_model
            
        except Exception as e:
            # Fallback to next available model
            remaining_providers = [p for p in self.model_preference if p != config.get("provider")]
            
            for fallback_provider in remaining_providers:
                if fallback_provider in available_models:
                    try:
                        fallback_config = available_models[fallback_provider]
                        fallback_config.update(kwargs)
                        
                        return ChatLiteLLM(
                            model=fallback_config["model"],
                            temperature=fallback_config.get("temperature", 0.1),
                            max_tokens=fallback_config.get("max_tokens", 4000),
                            api_key=fallback_config.get("api_key"),
                            api_base=fallback_config.get("api_base")
                        )
                    except Exception:
                        continue
            
            raise RuntimeError(f"Failed to create LLM model: {str(e)}")
    
    def _is_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            import requests
            response = requests.get(f"{self.ollama_base}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        preferred = self.get_preferred_model()
        available = self.get_available_models()
        
        return {
            "preferred_model": preferred,
            "available_models": list(available.keys()),
            "model_details": available,
            "litellm_available": LITELLM_AVAILABLE
        }


# Global configuration instance
llm_config = LLMConfig()


def get_chat_model(provider: Optional[str] = None, **kwargs) -> Any:
    """
    Convenience function to get a chat model.
    
    Args:
        provider: Specific provider (xai, ollama, openai)
        **kwargs: Additional model parameters
        
    Returns:
        Chat model instance
    """
    return llm_config.create_chat_model(provider=provider, **kwargs)


def get_model_info() -> Dict[str, Any]:
    """Get information about available models."""
    return llm_config.get_model_info()


def test_model_connection(provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Test connection to the specified model provider.
    
    Args:
        provider: Provider to test (xai, ollama, openai)
        
    Returns:
        Test results
    """
    try:
        model = get_chat_model(provider=provider)
        
        # Simple test prompt
        test_response = model.invoke("Hello! Please respond with 'Connection successful.'")
        
        return {
            "success": True,
            "provider": provider or "auto-selected",
            "response": str(test_response),
            "model_info": get_model_info()
        }
        
    except Exception as e:
        return {
            "success": False,
            "provider": provider or "auto-selected",
            "error": str(e),
            "model_info": get_model_info()
        }