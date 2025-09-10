"""
LiteLLM provider for KiroLinter AI Agent System.

This module provides a LangChain-compatible LLM interface using LiteLLM,
allowing the use of various LLM providers including xAI Grok, Ollama, OpenAI, etc.
"""

import os
from typing import Any, Dict, List, Optional, Union
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import LLMResult, Generation
from pydantic import Field

try:
    import litellm
    from dotenv import load_dotenv
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LiteLLMProvider(LLM):
    """
    LangChain-compatible LLM provider using LiteLLM.
    
    Supports multiple LLM providers:
    - xAI Grok: "xai/grok-code-fast-1"
    - Ollama: "ollama/llama2", "ollama/codellama", etc.
    - OpenAI: "gpt-4", "gpt-3.5-turbo"
    - Anthropic: "claude-3-sonnet-20240229"
    - And many more via LiteLLM
    """
    
    model: str = Field(default="xai/grok-code-fast-1", description="Model name for LiteLLM")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    api_base: Optional[str] = Field(default=None, description="API base URL for custom endpoints")
    api_key: Optional[str] = Field(default=None, description="API key for the model")
    verbose: bool = Field(default=False, description="Enable verbose/debug mode")
    
    def __init__(self, **kwargs):
        """Initialize LiteLLM provider with environment variables."""
        super().__init__(**kwargs)
        
        if not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM not available. Install with: pip install litellm")
        
        # Load environment variables
        load_dotenv()
        
        # Set up API keys from environment if not provided
        if not self.api_key:
            # Try different environment variable patterns
            env_keys = [
                "XAI_API_KEY",  # For xAI Grok
                "OPENAI_API_KEY",  # For OpenAI
                "ANTHROPIC_API_KEY",  # For Anthropic
                "LITELLM_API_KEY",  # Generic LiteLLM key
            ]
            
            for env_key in env_keys:
                if os.getenv(env_key):
                    self.api_key = os.getenv(env_key)
                    break
        
        # Configure LiteLLM based on verbose mode
        if self.api_key:
            if self.verbose:
                # Enable debug mode only when verbose is requested
                os.environ["LITELLM_LOG"] = "DEBUG"  
                litellm.set_verbose = True  
                litellm._turn_on_debug()
            else:
                # Use minimal logging in non-verbose mode
                os.environ["LITELLM_LOG"] = "ERROR"
                litellm.set_verbose = False
    
    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM."""
        return "litellm"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the LiteLLM API."""
        try:
            # Prepare arguments for LiteLLM
            call_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            }
            
            if self.max_tokens:
                call_kwargs["max_tokens"] = self.max_tokens
            
            if self.api_key:
                call_kwargs["api_key"] = self.api_key
            
            if self.api_base:
                call_kwargs["api_base"] = self.api_base
            
            if stop:
                call_kwargs["stop"] = stop
            
            # Add any additional kwargs
            call_kwargs.update(kwargs)
            
            # Make the API call
            response = litellm.completion(**call_kwargs)
            
            # Extract the response text
            return response.choices[0].message.content
            
        except Exception as e:
            # Provide helpful error messages for common issues
            error_msg = str(e)
            
            if "api_key" in error_msg.lower():
                raise ValueError(
                    f"API key error for model '{self.model}'. "
                    f"Please check your .env file and ensure the correct API key is set. "
                    f"Error: {error_msg}"
                )
            elif "model" in error_msg.lower():
                raise ValueError(
                    f"Model '{self.model}' not available or not supported. "
                    f"Please check the model name and your API access. "
                    f"Error: {error_msg}"
                )
            else:
                raise ValueError(f"LiteLLM call failed: {error_msg}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the LLM provider."""
        try:
            test_prompt = "Hello! Please respond with 'Connection successful' to test the API."
            response = self._call(test_prompt)
            
            return {
                "success": True,
                "model": self.model,
                "response": response,
                "message": "Connection test successful"
            }
            
        except Exception as e:
            return {
                "success": False,
                "model": self.model,
                "error": str(e),
                "message": "Connection test failed"
            }
    
    @classmethod
    def get_available_models(cls) -> Dict[str, List[str]]:
        """Get list of available models by provider."""
        return {
            "xai": ["xai/grok-code-fast-1", "xai/grok-3-mini"],  # Latest code-optimized model
            "ollama": [
                "ollama/llama3.1:8b",
                "ollama/gemma3n:e4b", 
                "ollama/qwen3:8b",
                "ollama/gemma3:12b-modified",
                "ollama/gemma3n:e2b",
                "ollama/llama4:scout",
                "ollama/gemma3:12b"
            ],
            "openai": [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k"
            ],
            "anthropic": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ],
            "google": [
                "gemini-pro",
                "gemini-pro-vision"
            ]
        }
    
    @classmethod
    def create_for_provider(cls, provider: str, model: Optional[str] = None, **kwargs) -> "LiteLLMProvider":
        """Create LiteLLM provider for specific provider."""
        available_models = cls.get_available_models()
        
        if provider not in available_models:
            raise ValueError(
                f"Provider '{provider}' not supported. "
                f"Available providers: {list(available_models.keys())}"
            )
        
        if not model:
            # Use first available model for the provider
            model = available_models[provider][0]
        
        return cls(model=model, **kwargs)


def create_llm_provider(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    verbose: bool = False,
    **kwargs
) -> LiteLLMProvider:
    """
    Factory function to create LLM provider with smart defaults.
    
    Args:
        model: Specific model name (e.g., "xai/grok-code-fast-1", "ollama/llama2")
        provider: Provider name (e.g., "xai", "ollama", "openai")
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        verbose: Enable verbose/debug mode
        **kwargs: Additional arguments for LiteLLMProvider
    
    Returns:
        Configured LiteLLMProvider instance
    """
    # Load environment variables
    load_dotenv()
    
    # Create provider
    if provider:
        # When provider is specified, let create_for_provider handle model selection
        return LiteLLMProvider.create_for_provider(
            provider=provider,
            model=model,  # This can be None, create_for_provider will choose default
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=verbose,
            **kwargs
        )
    else:
        # Only use environment-based model selection when no provider is specified
        if not model:
            # Check environment variable for preferred model
            model = os.getenv("KIROLINTER_LLM_MODEL")
            
            if not model:
                # Smart defaults based on available API keys
                if os.getenv("XAI_API_KEY"):
                    xai_model = os.getenv("XAI_MODEL_NAME", "grok-code-fast-1")
                    # Add xai/ prefix if not already present
                    model = xai_model if xai_model.startswith("xai/") else f"xai/{xai_model}"
                elif os.getenv("OPENAI_API_KEY"):
                    model = "gpt-4"
                elif os.getenv("ANTHROPIC_API_KEY"):
                    model = "claude-3-sonnet-20240229"
                else:
                    # Default to Ollama (local)
                    ollama_model = os.getenv("OLLAMA_MODEL_NAME", "llama2")
                    model = ollama_model if ollama_model.startswith("ollama/") else f"ollama/{ollama_model}"
        
        return LiteLLMProvider(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=verbose,
            **kwargs
        )