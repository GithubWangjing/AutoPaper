import os
import json
import logging
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

    def process(self, topic, paper_content):
        """Process the review task for a given paper."""
        logger.info(f"Starting review process for paper on topic: {topic}")
        
        try:
            # Process paper content
            if not paper_content or len(paper_content) < 100:
                logger.warning("Paper content is too short or empty")
                error_message = ["Error: 提供的论文内容不足，无法进行完整评审", "建议增加更多内容后再次提交"]
                self.progress = 0
                # Return the list directly, don't encode to JSON string
                return error_message
            
            # Generate feedback for the paper
            feedback = self._generate_feedback(topic, paper_content)
            logger.info("Feedback generated successfully")
            
            # Set progress to 100% to indicate completion
            self.progress = 100
            # Return the list directly, don't encode to JSON string
            return feedback
            
        except Exception as e:
            logger.error(f"Error in review process: {str(e)}")
            error_message = [
                f"Error: 评审过程中出现错误 - {str(e)}",
                "建议检查系统设置或稍后重试"
            ]
            self.progress = 0
            # Return the list directly, don't encode to JSON string
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
            
            # Call the language model API
            logger.info("Calling language model API for paper review")
            response = self._make_api_call(prompt)
            
            # Process the response
            if not response or response.startswith("API"):
                logger.error(f"API call failed: {response}")
                raise Exception(f"Language model API call failed: {response}")
                
            # Try to extract list items from the response
            feedback_lines = []
            
            # First try to parse as JSON if the response looks like a JSON array
            if response.strip().startswith("[") and response.strip().endswith("]"):
                try:
                    feedback_lines = json.loads(response)
                except json.JSONDecodeError:
                    pass
            
            # If JSON parsing failed, try to extract list items manually
            if not feedback_lines:
                for line in response.split("\n"):
                    line = line.strip()
                    # Look for numbered items or bullet points
                    if (line.startswith("-") or 
                        line.startswith("*") or 
                        (line[0].isdigit() and line[1:3] in [". ", ") ", "、"])):
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
            return [response, f"评审时间: {timestamp}"]
            
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            raise Exception(f"Failed to generate review feedback: {str(e)}")
    
    def get_progress(self):
        """Return the current progress of the review task."""
        return self.progress