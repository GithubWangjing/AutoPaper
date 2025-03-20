import os
import time
import json
import logging
import requests
from openai import OpenAI
from openai import RateLimitError, APIError, APITimeoutError
from .google_scholar import GoogleScholar
from .scholarly_google import ScholarlyGoogle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCP:
    """Model Content Provider - handles external API access for content retrieval."""
    
    def __init__(self, api_key=None, timeout=30, max_retries=3, base_delay=1.0):
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Initialize Google Scholar clients
        # Try to use ScholarlyGoogle by default (no API key needed)
        self.scholarly_google = ScholarlyGoogle(
            timeout=timeout,
            max_retries=max_retries,
            base_delay=base_delay
        )
        
        # Fall back to SerpAPI if API key is provided
        self.google_scholar = None
        if self.api_key:
            self.google_scholar = GoogleScholar(
                api_key=self.api_key,
                timeout=timeout,
                max_retries=max_retries,
                base_delay=base_delay
            )
            
        # Initialize OpenAI client for compatibility with existing code
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            timeout=timeout,
            max_retries=max_retries
        )
        
    @property
    def chat(self):
        """Get the chat completions interface."""
        return self.client.chat
        
    def chat_completions_create(self, **kwargs):
        """Create a chat completion with OpenAI API."""
        return self.client.chat.completions.create(**kwargs)
        
    def chat_completions(self):
        """Get the chat completions interface."""
        return self.client.chat.completions
        
    def search_papers(self, query, max_results=10):
        """Search for academic papers using Google Scholar.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        try:
            # First try using the scholarly library (no API key needed)
            try:
                logger.info("Trying to search papers using scholarly (no API key required)")
                results = self.scholarly_google.search(query, max_results=max_results)
                if results.get('papers'):
                    return results
            except Exception as e:
                logger.warning(f"Scholarly search failed: {str(e)}. Trying alternative method...")
            
            # If scholarly fails and we have an API key, try using SerpAPI
            if self.google_scholar:
                logger.info("Trying to search papers using SerpAPI")
                results = self.google_scholar.search(query, max_results=max_results)
                return results
            else:
                raise ValueError("No working Google Scholar search method available")
                
        except Exception as e:
            logger.error(f"Error searching for papers: {str(e)}")
            # Return empty results on error
            return {
                "papers": [],
                "error": str(e),
                "query": query,
                "timestamp": time.time(),
                "source": "google_scholar_error"
            } 