import os
import json
import logging
import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, model_type="siliconflow", custom_model_config=None):
        """Initialize the agent with configuration settings.
        
        Args:
            model_type: Type of model API to use (siliconflow, openai, anthropic, etc.)
            custom_model_config: Custom model configuration (for 'custom' model_type)
        """
        self.progress = 0
        self.model_type = model_type.lower()
        self.custom_model_config = custom_model_config
        
        # Set API configurations based on model type
        if self.model_type == "siliconflow":
            self.model = os.getenv("DEFAULT_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
            self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
            self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        elif self.model_type == "openai":
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
            self.api_key = os.getenv("OPENAI_API_KEY", "")
            self.api_url = "https://api.openai.com/v1/chat/completions"
        elif self.model_type == "anthropic":
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.api_url = "https://api.anthropic.com/v1/messages"
        elif self.model_type == "gemini":
            self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
            self.api_key = os.getenv("GEMINI_API_KEY", "")
            self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
        elif self.model_type == "glm":
            self.model = os.getenv("GLM_MODEL", "glm-4")
            self.api_key = os.getenv("GLM_API_KEY", "")
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        elif self.model_type == "qwen":
            self.model = os.getenv("QWEN_MODEL", "qwen-max")
            self.api_key = os.getenv("QWEN_API_KEY", "")
            self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        elif self.model_type == "zhipu":
            self.model = os.getenv("ZHIPU_MODEL", "glm-4")
            self.api_key = os.getenv("ZHIPU_API_KEY", "")
            self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        elif self.model_type == "baidu":
            self.model = os.getenv("BAIDU_MODEL", "ernie-4.0")
            self.api_key = os.getenv("BAIDU_API_KEY", "")
            self.api_url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
        elif self.model_type == "custom" and custom_model_config:
            # 设置自定义模型配置
            self.model = custom_model_config.get("model_name", "custom-model")
            self.api_key = custom_model_config.get("api_key", "")
            self.api_url = custom_model_config.get("endpoint", "")
            self.temperature = float(custom_model_config.get("temperature", 0.7))
            self.max_tokens = int(custom_model_config.get("max_tokens", 2000))
        else:
            # 默认使用siliconflow
            self.model = os.getenv("DEFAULT_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
            self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
            self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        
        # 通用配置
        if not hasattr(self, 'temperature'):
            self.temperature = float(os.getenv("DEFAULT_TEMPERATURE", 0.7))
        if not hasattr(self, 'max_tokens'):
            self.max_tokens = int(os.getenv("MAX_TOKENS", 2000))
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", 60))
        
        logger.info(f"Initialized {self.__class__.__name__} with model type {self.model_type}, model {self.model}")

    def _make_api_call(self, messages):
        """Make an API call to the AI model with retry mechanism."""
        logger.info(f"Making API call to {self.model_type} with {len(messages)} messages")
        
        max_retries = 3
        retry_delay = 5  # seconds
        
        for retry_count in range(max_retries):
            try:
                # 基础头部
                headers = {
                    "Content-Type": "application/json"
                }
                
                # 根据不同API类型设置不同的请求格式
                if self.model_type == "anthropic":
                    # Claude API格式
                    headers["x-api-key"] = self.api_key
                    headers["anthropic-version"] = "2023-06-01"
                    
                    # 转换消息格式
                    system_message = ""
                    conversation = []
                    
                    for msg in messages:
                        if msg["role"] == "system":
                            system_message = msg["content"]
                        elif msg["role"] in ["user", "assistant"]:
                            conversation.append(msg)
                    
                    data = {
                        "model": self.model,
                        "messages": conversation,
                        "system": system_message,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
                    }
                elif self.model_type == "gemini":
                    # Google Gemini API格式
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    # 转换消息格式为Gemini格式
                    gemini_messages = []
                    for msg in messages:
                        if msg["role"] == "user":
                            gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
                        elif msg["role"] == "assistant":
                            gemini_messages.append({"role": "model", "parts": [{"text": msg["content"]}]})
                        # system消息在Gemini中会加入到第一个用户消息中
                    
                    data = {
                        "contents": gemini_messages,
                        "generationConfig": {
                            "temperature": self.temperature,
                            "maxOutputTokens": self.max_tokens,
                        }
                    }
                else:
                    # OpenAI兼容格式 (适用于OpenAI、SiliconFlow、GLM等)
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    data = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    }
                
                # 发送请求
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                
                # 处理响应
                if response.status_code == 200:
                    result = response.json()
                    
                    # 根据不同API类型解析响应
                    if self.model_type == "anthropic":
                        if "content" in result and result["content"]:
                            content = result["content"][0]["text"]
                            self.progress = 100
                            return content
                    elif self.model_type == "gemini":
                        if "candidates" in result and result["candidates"]:
                            content = result["candidates"][0]["content"]["parts"][0]["text"]
                            self.progress = 100
                            return content
                    else:
                        # OpenAI兼容格式
                        if "choices" in result and len(result["choices"]) > 0:
                            self.progress = 100
                            return result["choices"][0]["message"]["content"].strip()
                
                # 处理错误响应
                error_msg = f"API error ({self.model_type}): {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # If we're not on the last retry, wait and try again
                if retry_count < max_retries - 1:
                    wait_time = retry_delay * (retry_count + 1)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{max_retries})")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    # Last retry failed
                    self.progress = 0
                    return f"API调用失败，状态码: {response.status_code}"
            
            except requests.exceptions.Timeout:
                # Handle timeout specifically
                error_msg = f"API timeout ({self.model_type}): Connection timed out"
                logger.error(error_msg)
                
                # Fall back to local/alternative model if available
                if self.model_type == "openai" and "siliconflow" != self.model_type:
                    logger.info("Falling back to SiliconFlow model due to OpenAI timeout")
                    # Save original settings
                    orig_model_type = self.model_type
                    orig_model = self.model
                    orig_api_key = self.api_key
                    orig_api_url = self.api_url
                    
                    # Temporarily switch to SiliconFlow
                    self.model_type = "siliconflow"
                    self.model = os.getenv("DEFAULT_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
                    self.api_key = os.getenv("SILICONFLOW_API_KEY", "")
                    self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
                    
                    # Make the call
                    try:
                        result = self._make_api_call(messages)
                        # If successful, return the result
                        return result
                    except Exception:
                        # If fallback fails, restore original settings
                        pass
                    finally:
                        # Restore original settings
                        self.model_type = orig_model_type
                        self.model = orig_model
                        self.api_key = orig_api_key
                        self.api_url = orig_api_url
                
                # If we're not on the last retry, wait and try again
                if retry_count < max_retries - 1:
                    wait_time = retry_delay * (retry_count + 1)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{max_retries})")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    # Last retry failed
                    self.progress = 0
                    return "API连接超时，请检查网络连接或使用其他模型"
            
            except Exception as e:
                # Handle other exceptions
                error_msg = f"API调用异常 ({self.model_type}): {str(e)}"
                logger.error(error_msg)
                
                # If we're not on the last retry, wait and try again
                if retry_count < max_retries - 1:
                    wait_time = retry_delay * (retry_count + 1)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{max_retries})")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    # Last retry failed
                    self.progress = 0
                    return f"API调用出错: {str(e)}"
    
    def get_progress(self):
        """Get the current progress percentage of the agent's task."""
        return self.progress
    
    def test_connection(self):
        """Test the connection to the model API."""
        logger.info(f"测试连接到 {self.model_type}")
        
        try:
            # 发送简单的测试消息
            test_message = [{"role": "user", "content": "Hello"}]
            result = self._make_api_call(test_message)
            
            if result and not result.startswith("API"):
                return {"status": "success", "message": f"连接到{self.model_type}成功", "response": result}
            else:
                return {"status": "error", "message": result}
        except Exception as e:
            return {"status": "error", "message": f"连接测试失败: {str(e)}"}
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Process a request - to be implemented by subclasses."""
        pass