import os
import json
import logging
from datetime import datetime
from .base_agent import BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WritingAgent(BaseAgent):
    """Agent responsible for writing academic papers based on research."""

    def __init__(self, model_type="siliconflow", custom_model_config=None):
        """Initialize the writing agent.
        
        Args:
            model_type: Type of model to use for text generation
            custom_model_config: Custom model configuration for custom model types
        """
        super().__init__(model_type=model_type, custom_model_config=custom_model_config)
        self.name = "Writing Agent"
        self.description = "Writes academic papers based on research findings"

    def process(self, topic, research_data):
        """Process the writing task for a given topic and research data."""
        logger.info(f"Starting writing process on topic: {topic}")
        
        try:
            # Parse research data if it's a string
            if isinstance(research_data, str):
                try:
                    research_data = json.loads(research_data)
                except json.JSONDecodeError:
                    research_data = {"content": research_data}
            
            # Generate a paper based on the topic and research
            paper_content = self._generate_paper(topic, research_data)
            logger.info("Paper draft created successfully")
            
            # Set progress to 100% to indicate completion
            self.progress = 100
            return paper_content
            
        except Exception as e:
            logger.error(f"Error in writing process: {str(e)}")
            error_message = f"# Error in Paper Generation\n\nAn error occurred while generating the paper: {str(e)}\n\nPlease try again or contact support if the issue persists."
            self.progress = 0
            return error_message
    
    def _generate_paper(self, topic, research_data):
        """Generate a paper based on the research data using the language model."""
        logger.info(f"Generating paper for topic: {topic}")
        
        # Extract information from research data
        summary = research_data.get("summary", "")
        papers = research_data.get("papers", [])
        content = research_data.get("content", "")
        
        # Create a comprehensive prompt for the language model
        paper_titles = [p.get("title", "") for p in papers[:5] if p.get("title")]
        paper_titles_text = "\n".join([f"- {title}" for title in paper_titles])
        
        prompt = [
            {"role": "system", "content": f"你是一位专业的学术论文写作专家，擅长以清晰、专业的学术风格撰写综述类论文。请基于提供的研究资料，为主题「{topic}」撰写一篇完整的学术论文。论文应包含标题、摘要、引言、方法与材料、研究结果、讨论、结论和参考文献等章节。论文应具有专业的学术风格，逻辑清晰，论证严谨。"},
            {"role": "user", "content": f"""请为主题「{topic}」撰写一篇完整的学术论文。以下是相关研究资料：

# 研究摘要
{summary}

# 相关论文
{paper_titles_text}

# 研究内容
{content}

请撰写一篇包含以下结构的完整学术论文：
1. 标题（应与主题「{topic}」相关）
2. 摘要
3. 引言（介绍研究背景、意义和目的）
4. 方法与材料（描述研究方法和数据来源）
5. 研究结果（详细展示研究发现）
6. 讨论（分析研究结果的意义、局限性及未来研究方向）
7. 结论（总结研究发现和贡献）
8. 参考文献（基于提供的相关论文）

请确保论文的标题为"# {topic}：研究现状与发展趋势"，并使用Markdown格式排版。
"""}
        ]
        
        # Call the language model API
        self.progress = 50
        logger.info("Calling language model API for paper generation")
        paper_content = self._make_api_call(prompt)
        
        # Check if the API call failed
        if not paper_content or paper_content.startswith("API"):
            logger.error(f"API call failed: {paper_content}")
            raise Exception(f"Language model API call failed: {paper_content}")
        
        self.progress = 100
        return paper_content

    def revise_draft(self, draft_content, feedback):
        """根据审阅反馈修改论文草稿。"""
        logger.info("开始根据反馈修改论文草稿")
        
        try:
            # 处理反馈数据
            feedback_points = []
            
            if isinstance(feedback, str):
                try:
                    # Try to parse it as JSON
                    feedback_data = json.loads(feedback)
                    feedback_points = feedback_data if isinstance(feedback_data, list) else [feedback]
                except json.JSONDecodeError:
                    # If not valid JSON, split by lines
                    feedback_points = [line.strip() for line in feedback.split("\n") if line.strip()]
            elif isinstance(feedback, list):
                # If already a list, use it directly
                feedback_points = feedback
            else:
                # If unknown type, convert to string
                feedback_points = [str(feedback)]
            
            # Remove any timestamps or metadata
            filtered_points = []
            for point in feedback_points:
                if not (point.startswith("评审时间:") or point.startswith("Error:") or point.startswith("WARNING:")):
                    filtered_points.append(point)
            
            # If no valid feedback points, use some defaults
            if not filtered_points:
                filtered_points = ["请改进论文结构和内容", "增加数据支持", "完善论述"]
                logger.warning("No valid feedback points found, using defaults")
            
            # 构建修改提示
            feedback_summary = "\n".join([f"- {point}" for point in filtered_points])
            
            prompt = [
                {"role": "system", "content": "你是一个学术写作专家，负责根据审阅反馈修改论文。请保持论文的整体结构，同时根据反馈意见进行改进。返回完整的修改后论文。"},
                {"role": "user", "content": f"以下是原始论文草稿:\n\n{draft_content}\n\n以下是审阅反馈:\n\n{feedback_summary}\n\n请根据反馈修改论文，提升其学术质量。保留原论文的结构，但解决反馈中指出的问题。返回完整的修改后论文。"}
            ]
            
            # 调用API进行修改
            self.progress = 50
            revised_content = self._make_api_call(prompt)
            
            # 如果API调用失败，抛出异常
            if not revised_content or revised_content.startswith("API"):
                logger.error(f"API调用失败: {revised_content}")
                raise Exception(f"Language model API call failed: {revised_content}")
            
            self.progress = 100
            logger.info("论文修订完成")
            return revised_content
            
        except Exception as e:
            logger.error(f"修订论文时出错: {str(e)}")
            self.progress = 0
            error_message = f"# 修订失败\n\n由于技术原因，无法完成论文修订: {str(e)}\n\n请稍后重试或联系系统管理员。"
            return error_message

    def get_progress(self):
        """Return the current progress of the writing task."""
        return self.progress 