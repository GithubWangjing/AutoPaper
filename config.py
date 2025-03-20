"""
Configuration file for the Academic Agent Suite.

This file contains configuration settings for the application, including API keys.
You can modify this file directly or use environment variables / .env file.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
# Priority: 1. Environment variable 2. Value in this file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# SiliconFlow API configuration (if used)
# Priority: 1. Environment variable 2. Value in this file
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "sk-nlubfdtqdcichcnddbklojwebahiqgzzyvhuricbzatfbbcr")

# Academic Paper API configuration
# SerpAPI for Google Scholar (if used, but optional now)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")  # Get your key from https://serpapi.com/

# Use scholarly library for Google Scholar (free, no API key needed)
USE_SCHOLARLY = os.getenv("USE_SCHOLARLY", "True").lower() == "true"

# ArXiv API configuration (free, no API key required)
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", 5))
ARXIV_SORT_BY = os.getenv("ARXIV_SORT_BY", "relevance")  # Options: "relevance", "lastUpdatedDate", "submittedDate"

# Model and Research Source Configuration
# Valid model types: "openai", "siliconflow"
DEFAULT_MODEL_TYPE = os.getenv("DEFAULT_MODEL_TYPE", "openai")

# Valid research sources: "none", "arxiv", "pubmed"
DEFAULT_RESEARCH_SOURCE = os.getenv("DEFAULT_RESEARCH_SOURCE", "arxiv")

# App configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.environ.get("PORT", 5000))
HOST = os.environ.get("HOST", "0.0.0.0")

# API request configuration
REQUEST_TIMEOUT = 180  # Increased timeout for longer API requests
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
BASE_DELAY = float(os.getenv("BASE_DELAY", 1.0))  # Base delay for retries in seconds

# Additional configuration
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "default_secret_key_change_this")
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///paper_projects.db")
MAX_TOKENS = 8000  # Increased token limit for larger responses 