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
        analysis = research_data.get("analysis", {})
        key_findings = analysis.get("key_findings", [])
        methodologies = analysis.get("methodologies", [])
        research_gaps = analysis.get("research_gaps", [])
        
        # Format reference information
        references = []
        for i, paper in enumerate(papers[:10]):  # Limit to 10 references
            authors = paper.get("authors", [])
            author_text = ", ".join(authors[:3])
            if len(authors) > 3:
                author_text += " et al."
                
            year = paper.get("year", "")
            title = paper.get("title", "")
            journal = paper.get("journal", "Unknown Journal")
            
            # Format in academic citation style
            ref = f"{author_text} ({year}). {title}. *{journal}*."
            references.append(f"[{i+1}] {ref}")
        
        references_text = "\n\n".join(references)
        
        # Format key findings, methodologies and research gaps
        key_findings_text = "\n".join([f"- {finding}" for finding in key_findings])
        methodologies_text = "\n".join([f"- {method}" for method in methodologies])
        research_gaps_text = "\n".join([f"- {gap}" for gap in research_gaps])
        
        # Create a comprehensive prompt for the language model with improved paper structure
        prompt = [
            {"role": "system", "content": f"""You are an expert academic writer specializing in creating professionally formatted research papers. 
            Create a complete academic paper on the topic '{topic}' using the provided research materials.
            
            Format the paper using proper academic structure with these sections:
            1. Title: Should be centered, bold, and descriptive
            2. Abstract: A concise summary of the paper (150-250 words)
            3. Introduction: Background, significance, research questions
            4. Literature Review: Analysis of existing research
            5. Methodology: Approaches used in the field
            6. Results and Discussion: Key findings and their implications
            7. Future Research Directions: Gaps and opportunities
            8. Conclusion: Summary of contributions
            9. References: Properly formatted citations
            
            Use academic language, maintain logical flow between sections, and ensure proper citation of sources."""},
            
            {"role": "user", "content": f"""Please write a comprehensive academic paper on the topic "{topic}" following proper academic formatting and structure.

Here is the research material to incorporate:

SUMMARY OF RESEARCH:
{summary}

KEY FINDINGS FROM LITERATURE:
{key_findings_text}

METHODOLOGIES IDENTIFIED:
{methodologies_text}

RESEARCH GAPS:
{research_gaps_text}

REFERENCES TO CITE:
{references_text}

Please format the paper with clear section headers (# for main headers, ## for subheaders) and include:
1. A descriptive title
2. An informative abstract
3. A comprehensive introduction setting the context
4. A thorough literature review section analyzing existing research
5. A methodology section describing research approaches
6. Results and discussion of key findings
7. Future research directions based on identified gaps
8. A conclusion summarizing the paper's contributions
9. Properly formatted references section

The paper should be scholarly in tone, use appropriate academic terminology, and maintain logical flow between sections.
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
        
        # Add formatting improvements if needed
        if not paper_content.startswith('# '):
            paper_content = f"# {topic}: A Comprehensive Review\n\n{paper_content}"
        
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