"""
Paper Types Configuration

This module defines different academic paper types with their structures and guidelines.
"""

PAPER_TYPES = {
    "regular": {
        "name": "Regular Research Paper",
        "description": "A full-length research paper presenting original research with comprehensive methods and results.",
        "sections": [
            "Abstract",
            "Introduction",
            "Materials and Methods",
            "Results",
            "Discussion",
            "Conclusion",
            "References"
        ],
        "word_count": "4000-8000 words",
        "figures": "4-8 figures"
    },
    "letter": {
        "name": "Letter",
        "description": "A short, focused paper reporting novel and significant findings that require rapid publication.",
        "sections": [
            "Abstract",
            "Introduction",
            "Results and Discussion",
            "Methods",
            "References"
        ],
        "word_count": "1500-2500 words",
        "figures": "2-3 figures"
    },
    "review": {
        "name": "Review Paper",
        "description": "A comprehensive analysis and discussion of existing literature on a specific topic.",
        "sections": [
            "Abstract",
            "Introduction",
            "Background/Literature Review",
            "Current State of Knowledge",
            "Future Directions",
            "Conclusion",
            "References"
        ],
        "word_count": "5000-10000 words",
        "figures": "5-10 figures"
    },
    "technical_note": {
        "name": "Technical Note",
        "description": "A brief paper describing novel techniques, methods, or tools.",
        "sections": [
            "Abstract",
            "Introduction",
            "Technical Description",
            "Application Example",
            "Discussion",
            "References"
        ],
        "word_count": "2000-3000 words",
        "figures": "2-4 figures"
    },
    "case_study": {
        "name": "Case Study",
        "description": "An in-depth analysis of a specific case, event, or implementation.",
        "sections": [
            "Abstract",
            "Introduction",
            "Case Description",
            "Methods/Approach",
            "Results",
            "Discussion",
            "Conclusion",
            "References"
        ],
        "word_count": "3000-5000 words",
        "figures": "3-6 figures"
    },
    "perspective": {
        "name": "Perspective/Opinion Paper",
        "description": "A paper presenting the author's opinion or perspective on a specific topic.",
        "sections": [
            "Abstract",
            "Introduction",
            "Main Arguments",
            "Implications",
            "Conclusion",
            "References"
        ],
        "word_count": "2000-4000 words",
        "figures": "1-3 figures"
    },
    "survey": {
        "name": "Survey Paper",
        "description": "A comprehensive overview of a research area with categorization and classification of existing work.",
        "sections": [
            "Abstract",
            "Introduction",
            "Survey Methodology",
            "Classification Framework",
            "Literature Review by Categories",
            "Open Challenges and Future Directions",
            "Conclusion",
            "References"
        ],
        "word_count": "6000-12000 words",
        "figures": "6-12 figures"
    }
}

# Language options for papers
LANGUAGE_OPTIONS = {
    "en": {
        "name": "English",
        "description": "Standard academic English suitable for international publications."
    },
    "en_us": {
        "name": "English (US)",
        "description": "American English with US spelling conventions."
    },
    "en_uk": {
        "name": "English (UK)",
        "description": "British English with UK spelling conventions."
    },
    "zh": {
        "name": "Chinese",
        "description": "Academic Chinese for publications in Chinese-language journals."
    },
    "fr": {
        "name": "French",
        "description": "Academic French for publications in French-language journals."
    },
    "de": {
        "name": "German",
        "description": "Academic German for publications in German-language journals."
    },
    "es": {
        "name": "Spanish",
        "description": "Academic Spanish for publications in Spanish-language journals."
    },
    "ja": {
        "name": "Japanese",
        "description": "Academic Japanese for publications in Japanese-language journals."
    }
}

def get_paper_types():
    """Return all available paper types."""
    return PAPER_TYPES

def get_paper_type(type_id):
    """Return a specific paper type by its ID."""
    return PAPER_TYPES.get(type_id, PAPER_TYPES["regular"])

def get_languages():
    """Return all available language options."""
    return LANGUAGE_OPTIONS

def get_language(lang_id):
    """Return a specific language by its ID."""
    return LANGUAGE_OPTIONS.get(lang_id, LANGUAGE_OPTIONS["en"])

def generate_template(paper_type_id, language_id="en"):
    """
    Generate a template structure for a specified paper type in the selected language.
    
    Args:
        paper_type_id (str): The ID of the paper type
        language_id (str): The ID of the language
        
    Returns:
        dict: A template structure for the paper
    """
    paper_type = get_paper_type(paper_type_id)
    language = get_language(language_id)
    
    template = {
        "paper_type": paper_type["name"],
        "language": language["name"],
        "sections": paper_type["sections"],
        "guidelines": {
            "word_count": paper_type["word_count"],
            "figures": paper_type["figures"]
        }
    }
    
    return template 