"""
LLM Client for Ollama API.
Handles all communication with the gemma3:27b model.
"""

import httpx
import logging
import json
from typing import Dict, Any, Optional, List
from src.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.MODEL_NAME
        self.vision_model = settings.VISION_MODEL
        self.timeout = settings.LLM_TIMEOUT
        self.vision_timeout = settings.VISION_TIMEOUT
        
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Generate text completion from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction (optional)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output
            
        Returns:
            Dict with 'response' key containing generated text
            
        Raises:
            Exception: If API call fails
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
                
            if json_mode:
                payload["format"] = "json"
            
            logger.info(f"Sending request to Ollama: {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
            result = response.json()
            logger.info(f"Received response from Ollama (length: {len(result.get('response', ''))})")
            logger.debug(f"Response: {result.get('response', '')[:500]}")
            
            return result
            
        except httpx.TimeoutException as e:
            logger.error(f"Ollama API timeout: {str(e)}")
            raise Exception(f"LLM request timed out after {self.timeout}s")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API returned error: {e.response.status_code}")
            
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama server: {str(e)}")
            raise Exception(f"Cannot reach Ollama server at {self.base_url}")
            
        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {str(e)}", exc_info=True)
            raise Exception(f"LLM request failed: {str(e)}")
    
    async def generate_with_vision(
        self,
        prompt: str,
        image_data: bytes,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate completion with vision input (for invoice images).
        Uses qwen3-vl:32b vision-language model.
        
        Args:
            prompt: Text prompt describing what to extract
            image_data: Raw image bytes
            system_prompt: System instruction
            temperature: Sampling temperature
            
        Returns:
            Dict with 'response' key containing generated text
        """
        try:
            import base64
            
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.vision_model,  # Use vision model here
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            logger.info(f"Sending vision request to Ollama with {self.vision_model} (image size: {len(image_data)} bytes)")
            logger.info(f"Using timeout: {self.vision_timeout}s for vision request")
            logger.debug(f"Prompt: {prompt[:200]}...")
            
            async with httpx.AsyncClient(timeout=self.vision_timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
            result = response.json()
            logger.info(f"Received vision response from {self.vision_model}")
            logger.debug(f"Response: {result.get('response', '')[:500]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Vision API error: {str(e)}", exc_info=True)
            raise Exception(f"Vision LLM request failed: {str(e)}")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Chat completion with message history.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Sampling temperature
            json_mode: Request JSON output
            
        Returns:
            Dict with response
        """
        try:
            url = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if json_mode:
                payload["format"] = "json"
            
            logger.info(f"Sending chat request to Ollama ({len(messages)} messages)")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
            result = response.json()
            logger.info(f"Received chat response from Ollama")
            
            return result
            
        except Exception as e:
            logger.error(f"Chat API error: {str(e)}", exc_info=True)
            raise Exception(f"Chat LLM request failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Ollama server is reachable and model is available.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if self.model in model_names:
                logger.info(f"Health check passed: {self.model} is available")
                return True
            else:
                logger.warning(f"Model {self.model} not found. Available: {model_names}")
                return False
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Singleton instance
ollama_client = OllamaClient()
