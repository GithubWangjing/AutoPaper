import os
import time
import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SiliconFlow:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", 60))
        
    def create_completion(self, model, messages, **kwargs):
        """Create a chat completion using direct API calls"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        
        logger.info(f"Making API call to {self.api_url}")
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            return {
                "choices": [
                    {"message": {"content": result["choices"][0]["message"]["content"]}}
                ]
            }
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise 