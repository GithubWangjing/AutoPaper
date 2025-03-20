import os
import json
import logging
from datetime import datetime
from .base_agent import BaseAgent
import re

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
                error_message = ["Error: The provided paper content is insufficient for a complete review", "Please add more content and submit again"]
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
                f"Error: An error occurred during the review process - {str(e)}",
                "Please check the system settings or try again later"
            ]
            self.progress = 0
            # Return the list directly, don't encode to JSON string
            return error_message
    
    def _generate_feedback(self, topic, paper_content):
        """Generate feedback for the paper using the language model."""
        try:
            # Create prompt for the model with improved instructions for Markdown formatting
            prompt = [
                {"role": "system", "content": "You are a rigorous academic paper reviewer with expertise in providing constructive feedback. Please conduct a comprehensive review of the provided paper using strict Markdown formatting. Each review section must contain detailed explanations and specific suggestions (at least 3-4 complete paragraphs). Ensure proper paragraph separation and spacing for better display. Your response must follow the required Markdown format, particularly maintaining spacing between paragraphs."},
                {"role": "user", "content": f"""Please review the following academic paper on the topic of "{topic}" and provide detailed feedback:

{paper_content[:10000]}

Please use the following Markdown format for your review, with each review point containing at least 3 detailed paragraphs, each paragraph having 3-5 sentences to ensure rich review details:

# Paper Review Report

## Innovation and Research Value

[Provide at least 3 detailed paragraphs describing the paper's innovation points and research value, analyzing its positioning and contribution in academia. Each paragraph must be separated by a blank line.]

## Systematic Research Methodology

[Provide at least 3 detailed paragraphs evaluating the selection, implementation, and effectiveness of the research methods. Each paragraph must be separated by a blank line.]

## Depth of Results Presentation

[Provide at least 3 detailed paragraphs evaluating the presentation of results, depth of data analysis, and validity of conclusions. Each paragraph must be separated by a blank line.]

## Potential Clinical Application Value

[Provide at least 3 detailed paragraphs analyzing the potential application value of the research in clinical practice. Each paragraph must be separated by a blank line.]

## Contribution to Existing Research

[Provide at least 3 detailed paragraphs analyzing how the paper extends and contributes to existing literature. Each paragraph must be separated by a blank line.]

## Recommendations for Future Research

[Provide at least 3 detailed paragraphs containing 3-5 specific, valuable suggestions for future research directions. Each paragraph must be separated by a blank line.]

Ensure each review section has complete discussion, not just brief comments. Each paragraph must contain 3-5 complete sentences, not short phrases. Paragraphs must be separated by blank lines to ensure correct Markdown rendering. The final review report should resemble a complete academic review article with professionalism and rigor.

Important: Ensure there are blank lines between headings, between paragraphs, and that each section has sufficient content (at least 3 paragraphs).
"""}
            ]
            
            # Update progress
            self.progress = 50
            
            # Call the language model API
            logger.info("Calling language model API for paper review")
            response = self._make_api_call(prompt)
            
            # Return the full Markdown response directly with improved formatting
            if response and isinstance(response, str) and len(response) > 100:
                # Add timestamp to the end of the Markdown
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Fix any formatting issues in the response
                formatted_response = response
                
                # Ensure adequate spacing between headings
                formatted_response = re.sub(r'(#+\s+[^\n]+)\n(?!#)', r'\1\n\n', formatted_response)
                
                # Ensure adequate spacing between text paragraphs
                formatted_response = re.sub(r'([^\n])\n([^\n#])', r'\1\n\n\2', formatted_response)
                
                # Ensure extra spacing before major headings
                formatted_response = re.sub(r'\n(#+\s+)', r'\n\n\1', formatted_response)
                
                # Fix potential punctuation formatting issues
                formatted_response = formatted_response.replace(':\n', ':\n\n')
                formatted_response = formatted_response.replace('.\n', '.\n\n')
                
                # Remove consecutive blank lines
                formatted_response = re.sub(r'\n{3,}', '\n\n', formatted_response)
                
                # Add timestamp
                markdown_response = f"{formatted_response}\n\n*Review Time: {timestamp}*"
                return markdown_response
            elif not response or not isinstance(response, str):
                logger.error(f"Invalid response from API: {response}")
                return f"""# Error in Review Process

Unable to obtain a valid review result. Please try again later.

*Review Time: {datetime.now().isoformat()}*
"""
            else:
                logger.warning("Response too short, might be an error")
                return f"""# Review Results

{response}

*Review Time: {datetime.now().isoformat()}*
"""
            
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            raise Exception(f"Failed to generate review feedback: {str(e)}")
    
    def get_progress(self):
        """Return the current progress of the review task."""
        return self.progress