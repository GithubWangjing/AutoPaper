import os
import json
import logging
import traceback
import requests
from datetime import datetime
from .base_agent import BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReviewAgent(BaseAgent):
    """Agent responsible for reviewing and providing feedback on academic papers."""

    def __init__(self, model_type="siliconflow", custom_model_config=None):
        """Initialize the review agent.
        
        Args:
            model_type: Type of model to use for text generation
            custom_model_config: Custom model configuration for custom model types
        """
        super().__init__(model_type=model_type, custom_model_config=custom_model_config)
        self.name = "Review Agent"
        self.description = "Reviews academic papers and provides feedback"
        self.progress = 0
    
    def test_connection(self):
        """Test the connection to the API service to identify potential issues."""
        try:
            logger.info(f"Testing API connection for model type: {self.model_type}")
            
            # Simple test prompt
            test_prompt = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, this is a connection test."}
            ]
            
            # Make a minimal API call
            response = self._make_api_call(test_prompt, max_tokens=20)
            
            if response and not response.startswith("API Error"):
                logger.info("API connection test successful")
                return {"status": "success", "message": "API connection successful"}
            else:
                logger.error(f"API connection test failed: {response}")
                return {"status": "error", "message": f"API connection failed: {response}"}
                
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Exception during API connection test: {str(e)}\n{error_details}")
            return {
                "status": "error",
                "message": f"API connection test failed with exception: {str(e)}",
                "details": error_details
            }

    def process(self, topic, paper_content):
        """Process the review task for a given paper."""
        logger.info(f"Starting review process for paper on topic: {topic}")
        
        try:
            # Process paper content
            if not paper_content:
                logger.warning("Paper content is empty")
                error_message = ["Error: 提供的论文内容为空，无法进行评审", "请确保论文内容已经准备好"]
                self.progress = 0
                return error_message
                
            if isinstance(paper_content, str) and len(paper_content) < 100:
                logger.warning("Paper content is too short")
                error_message = ["Error: 提供的论文内容不足，无法进行完整评审", "建议增加更多内容后再次提交"]
                self.progress = 0
                return error_message
            
            # First test the API connection
            connection_test = self.test_connection()
            if connection_test["status"] == "error":
                logger.error(f"API connection test failed before review: {connection_test['message']}")
                return [
                    f"Error: API连接测试失败 - {connection_test['message']}",
                    "请检查网络连接和API设置"
                ]
            
            # Generate feedback for the paper
            feedback = self._generate_feedback(topic, paper_content)
            logger.info("Feedback generated successfully")
            
            # Set progress to 100% to indicate completion
            self.progress = 100
            return feedback
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Error in review process: {str(e)}\n{error_details}")
            error_message = [
                f"Error: 评审过程中出现错误 - {str(e)}",
                "建议检查系统设置或稍后重试",
                f"详细错误: {error_details[:200]}..." if len(error_details) > 200 else f"详细错误: {error_details}"
            ]
            self.progress = 0
            return error_message
    
    def _generate_feedback(self, topic, paper_content):
        """Generate feedback for the paper using the language model."""
        try:
            # Create prompt for the model
            prompt = [
                {"role": "system", "content": "你是一位严谨的学术论文审稿人，擅长提供建设性的论文评审意见。请对提供的论文进行全面评审，关注论文结构、研究方法、数据分析、结论等方面，并以列表形式提供5-8条具体、有针对性的改进建议。"},
                {"role": "user", "content": f"请审阅以下关于「{topic}」的学术论文，并提供评审意见：\n\n{paper_content}\n\n请以列表形式提供5-8条具体的评审意见，重点关注论文的优点和需要改进的地方。"}
            ]
            
            # Update progress
            self.progress = 50
            
            # Call the language model API with error handling
            logger.info("Calling language model API for paper review")
            response = self._make_api_call(prompt)
            
            # Process the response
            if not response:
                logger.error("Empty API response")
                raise Exception("Language model API returned empty response")
                
            if isinstance(response, str) and response.startswith("API Error"):
                logger.error(f"API call failed: {response}")
                raise Exception(f"Language model API call failed: {response}")
                
            # Try to extract list items from the response
            feedback_lines = []
            
            # First try to parse as JSON if the response looks like a JSON array
            if isinstance(response, str) and response.strip().startswith("[") and response.strip().endswith("]"):
                try:
                    feedback_lines = json.loads(response)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse response as JSON array")
                    pass
            
            # If JSON parsing failed, try to extract list items manually
            if not feedback_lines:
                if isinstance(response, str):
                    for line in response.split("\n"):
                        line = line.strip()
                        # Look for numbered items or bullet points
                        if (line and (line.startswith("-") or 
                            line.startswith("*") or 
                            (len(line) > 2 and line[0].isdigit() and line[1:3] in [". ", ") ", "、"]))):
                            feedback_lines.append(line.lstrip("- *0123456789.、) "))
            
            # If we found list items, use them
            if feedback_lines:
                # Add timestamp to feedback
                timestamp = datetime.now().isoformat()
                feedback_lines.append(f"评审时间: {timestamp}")
                return feedback_lines
            
            # If no list items were found, use the whole response
            logger.warning("Could not parse response as list items, using full response")
            timestamp = datetime.now().isoformat()
            
            if isinstance(response, str):
                return [response, f"评审时间: {timestamp}"]
            else:
                # Handle non-string responses (rare case)
                return [str(response), f"评审时间: {timestamp}"]
            
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Error generating feedback: {str(e)}\n{error_details}")
            raise Exception(f"Failed to generate review feedback: {str(e)}")
    
    def get_progress(self):
        """Return the current progress of the review task."""
        return self.progress 