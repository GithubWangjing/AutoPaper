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
        
        # Break down paper generation into sections to avoid token limits
        paper_sections = {}
        
        # 1. Generate title and abstract
        logger.info("Generating title and abstract")
        title_abstract_prompt = [
            {"role": "system", "content": f"You are an expert academic writer. Create a title and abstract for a paper on '{topic}' based on the provided research."},
            {"role": "user", "content": f"""Create a title and abstract for an academic paper on "{topic}".
            
Summary of research: {summary[:1000]}
Key findings: {key_findings_text[:500]}
            
Format your response as:
# [Title]

## Abstract
[Abstract text, 150-250 words]
"""}
        ]
        
        self.progress = 10
        title_and_abstract = self._make_api_call(title_abstract_prompt)
        if not title_and_abstract or title_and_abstract.startswith("API"):
            logger.error(f"Failed to generate title and abstract: {title_and_abstract}")
            raise Exception("Failed to generate title and abstract")
        
        paper_sections["title_abstract"] = title_and_abstract
        
        # 2. Generate introduction
        logger.info("Generating introduction")
        intro_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create an introduction section for a research paper."},
            {"role": "user", "content": f"""Write an introduction section for an academic paper on "{topic}".
            
Summary of research: {summary[:1000]}
Key findings: {key_findings_text[:500]}
            
The introduction should include:
1. Background context
2. Significance of the research
3. Research objectives
4. Structure of the paper

Format your response as:
## Introduction
[Introduction text]
"""}
        ]
        
        self.progress = 20
        introduction = self._make_api_call(intro_prompt)
        if not introduction or introduction.startswith("API"):
            logger.error(f"Failed to generate introduction: {introduction}")
            raise Exception("Failed to generate introduction")
        
        paper_sections["introduction"] = introduction
        
        # 3. Generate literature review
        logger.info("Generating literature review")
        lit_review_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create a literature review section for a research paper."},
            {"role": "user", "content": f"""Write a literature review section for an academic paper on "{topic}".
            
Summary of research: {summary}
Key findings: {key_findings_text}
References to cite:
{references_text[:1000]}
            
The literature review should:
1. Analyze existing research
2. Identify trends and patterns
3. Evaluate methodological approaches
4. Identify gaps in the literature

Format your response as:
## Literature Review
[Literature review text]
"""}
        ]
        
        self.progress = 30
        literature_review = self._make_api_call(lit_review_prompt)
        if not literature_review or literature_review.startswith("API"):
            logger.error(f"Failed to generate literature review: {literature_review}")
            raise Exception("Failed to generate literature review")
        
        paper_sections["literature_review"] = literature_review
        
        # 4. Generate methodology
        logger.info("Generating methodology section")
        method_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create a methodology section for a research paper."},
            {"role": "user", "content": f"""Write a methodology section for an academic paper on "{topic}".
            
Methodologies identified: {methodologies_text}
            
The methodology section should:
1. Describe the research approach
2. Explain data collection methods
3. Outline analytical frameworks
4. Address limitations

Format your response as:
## Methodology
[Methodology text]
"""}
        ]
        
        self.progress = 40
        methodology = self._make_api_call(method_prompt)
        if not methodology or methodology.startswith("API"):
            logger.error(f"Failed to generate methodology: {methodology}")
            raise Exception("Failed to generate methodology")
        
        paper_sections["methodology"] = methodology
        
        # 5. Generate results and discussion
        logger.info("Generating results and discussion")
        results_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create a results and discussion section for a research paper."},
            {"role": "user", "content": f"""Write a results and discussion section for an academic paper on "{topic}".
            
Key findings: {key_findings_text}
Summary of research: {summary[:800]}
            
The results and discussion should:
1. Present key findings
2. Analyze and interpret results
3. Compare with existing literature
4. Discuss implications

Format your response as:
## Results and Discussion
[Results and discussion text]
"""}
        ]
        
        self.progress = 50
        results_discussion = self._make_api_call(results_prompt)
        if not results_discussion or results_discussion.startswith("API"):
            logger.error(f"Failed to generate results and discussion: {results_discussion}")
            raise Exception("Failed to generate results and discussion")
        
        paper_sections["results_discussion"] = results_discussion
        
        # 6. Generate future research directions
        logger.info("Generating future research directions")
        future_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create a future research directions section for a research paper."},
            {"role": "user", "content": f"""Write a future research directions section for an academic paper on "{topic}".
            
Research gaps: {research_gaps_text}
Key findings: {key_findings_text[:500]}
            
The future research section should:
1. Identify gaps in knowledge
2. Suggest potential research questions
3. Outline methodological improvements
4. Discuss potential applications

Format your response as:
## Future Research Directions
[Future research text]
"""}
        ]
        
        self.progress = 60
        future_research = self._make_api_call(future_prompt)
        if not future_research or future_research.startswith("API"):
            logger.error(f"Failed to generate future research directions: {future_research}")
            raise Exception("Failed to generate future research directions")
        
        paper_sections["future_research"] = future_research
        
        # 7. Generate conclusion
        logger.info("Generating conclusion")
        conclusion_prompt = [
            {"role": "system", "content": "You are an expert academic writer. Create a conclusion section for a research paper."},
            {"role": "user", "content": f"""Write a conclusion section for an academic paper on "{topic}".
            
Key findings: {key_findings_text[:500]}
            
The conclusion should:
1. Summarize the main findings
2. Restate the significance of the research
3. Discuss limitations
4. End with a strong closing statement

Format your response as:
## Conclusion
[Conclusion text]
"""}
        ]
        
        self.progress = 70
        conclusion = self._make_api_call(conclusion_prompt)
        if not conclusion or conclusion.startswith("API"):
            logger.error(f"Failed to generate conclusion: {conclusion}")
            raise Exception("Failed to generate conclusion")
        
        paper_sections["conclusion"] = conclusion
        
        # 8. Format references section
        logger.info("Formatting references")
        references_section = "## References\n\n" + "\n".join(references)
        paper_sections["references"] = references_section
        
        # Combine all sections
        logger.info("Combining all paper sections")
        paper_content = "\n\n".join([
            paper_sections["title_abstract"],
            paper_sections["introduction"],
            paper_sections["literature_review"],
            paper_sections["methodology"],
            paper_sections["results_discussion"],
            paper_sections["future_research"],
            paper_sections["conclusion"],
            paper_sections["references"]
        ])
        
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