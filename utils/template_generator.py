"""
Template Generator for Academic Papers

This module generates paper templates based on paper type and language.
"""

import os
from datetime import datetime

try:
    from utils.paper_types import get_paper_type, get_language
except ImportError:
    # Fallback definitions if paper_types.py is not available
    def get_paper_type(type_id):
        return {
            "name": "Regular Research Paper",
            "sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "References"],
            "word_count": "4000-8000 words",
            "figures": "4-8 figures"
        }
    
    def get_language(lang_id):
        return {
            "name": "English",
            "description": "Standard academic English"
        }

def get_section_template(section_name, language_id="en"):
    """
    Get template content for a specific section based on language.
    
    Args:
        section_name (str): The name of the section
        language_id (str): The language identifier
        
    Returns:
        str: Template content for the section
    """
    # English section templates
    en_templates = {
        "Abstract": "Write a concise summary of the paper's purpose, methods, results, and conclusions in 150-250 words.",
        "Introduction": "Provide background information, state the research problem, and outline the purpose and significance of the study.",
        "Literature Review": "Critically analyze and summarize existing research relevant to your topic.",
        "Materials and Methods": "Describe the research design, materials, procedures, and analysis methods in sufficient detail for replication.",
        "Results": "Present the findings of your research without interpretation, using tables and figures to support your data.",
        "Discussion": "Interpret your results, explain their significance, and relate them to existing literature. Address limitations and implications.",
        "Conclusion": "Summarize key findings and their importance, and suggest directions for future research.",
        "References": "List all sources cited in the paper following the appropriate citation style.",
        # Add templates for other sections
        "Background": "Provide comprehensive context for your research, explaining fundamental concepts and previous work.",
        "Survey Methodology": "Describe how you selected and analyzed the literature included in your survey.",
        "Technical Description": "Provide detailed technical specifications and implementation details.",
        "Case Description": "Describe the specific case being studied, including relevant background and context.",
        "Methods/Approach": "Explain the approach used to study or address the case.",
        "Main Arguments": "Present the key points supporting your perspective or opinion.",
        "Implications": "Discuss the broader implications of your arguments or findings.",
        "Future Directions": "Identify promising areas for future research in this field.",
        "Application Example": "Demonstrate the practical application of the described technique or method.",
        "Classification Framework": "Present the framework used to categorize and organize the surveyed literature.",
        "Literature Review by Categories": "Present and analyze the literature according to your classification framework.",
        "Open Challenges": "Discuss unresolved problems and challenges in the field.",
        "Results and Discussion": "Present and interpret your findings in a combined section."
    }
    
    # Templates for other languages could be added here
    zh_templates = {
        "摘要": "用150-250字简洁概述论文的目的、方法、结果和结论。",
        "引言": "提供研究背景信息，阐述研究问题，并概述研究的目的和意义。",
        "文献综述": "批判性分析和总结与您的主题相关的现有研究。",
        "材料与方法": "详细描述研究设计、材料、程序和分析方法，以便他人可以复制研究。",
        "结果": "呈现研究结果，不包含解释，使用表格和图形支持您的数据。",
        "讨论": "解释您的结果，阐明其意义，并将其与现有文献联系起来。讨论局限性和影响。",
        "结论": "总结关键发现及其重要性，并提出未来研究方向。",
        "参考文献": "按照适当的引用格式列出论文中引用的所有来源。"
    }
    
    # Select template based on language
    if language_id.startswith("zh"):
        # Map English section names to Chinese
        section_map = {
            "Abstract": "摘要",
            "Introduction": "引言",
            "Literature Review": "文献综述",
            "Materials and Methods": "材料与方法",
            "Results": "结果",
            "Discussion": "讨论",
            "Conclusion": "结论",
            "References": "参考文献"
        }
        
        # Try to get Chinese section name and template
        zh_section = section_map.get(section_name, section_name)
        content = zh_templates.get(zh_section, f"在此编写"{zh_section}"部分内容。")
    else:
        # Default to English templates
        content = en_templates.get(section_name, f"Write your {section_name} content here.")
    
    return content

def generate_paper_template(topic, paper_type_id="regular", language_id="en"):
    """
    Generate a complete paper template based on paper type and language.
    
    Args:
        topic (str): The paper topic
        paper_type_id (str): The paper type identifier
        language_id (str): The language identifier
        
    Returns:
        str: The complete paper template in Markdown format
    """
    paper_type = get_paper_type(paper_type_id)
    language = get_language(language_id)
    
    # Paper title and metadata
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Title and header based on language
    if language_id.startswith("zh"):
        title = f"# {topic}\n\n"
        author_line = "**作者：** [作者姓名]\n"
        date_line = f"**日期：** {today}\n"
        type_line = f"**论文类型：** {paper_type['name']}\n"
    else:
        title = f"# {topic}\n\n"
        author_line = "**Author:** [Author Name]\n"
        date_line = f"**Date:** {today}\n"
        type_line = f"**Paper Type:** {paper_type['name']}\n"
    
    # Build the template
    template = title + author_line + date_line + type_line + "\n"
    
    # Add sections based on paper type
    for section in paper_type["sections"]:
        template += f"## {section}\n\n"
        template += get_section_template(section, language_id) + "\n\n"
    
    # Add guidelines
    if language_id.startswith("zh"):
        template += "## 指南\n\n"
        template += f"- 字数：{paper_type['word_count']}\n"
        template += f"- 图表：{paper_type['figures']}\n"
    else:
        template += "## Guidelines\n\n"
        template += f"- Word count: {paper_type['word_count']}\n"
        template += f"- Figures: {paper_type['figures']}\n"
    
    return template

def save_template(template, project_id):
    """
    Save the generated template to a file.
    
    Args:
        template (str): The template content
        project_id (int): The project identifier
        
    Returns:
        str: Path to the saved template file
    """
    # Create templates directory if it doesn't exist
    os.makedirs('static/templates', exist_ok=True)
    
    # Save template to file
    filename = f"static/templates/project_{project_id}_template.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(template)
    
    return filename

if __name__ == "__main__":
    # Test the template generator
    template = generate_paper_template("Advances in AI Research", "survey", "en")
    print(template)
    
    # Test with Chinese
    template_zh = generate_paper_template("人工智能研究进展", "survey", "zh")
    print(template_zh) 