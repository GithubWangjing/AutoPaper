import os
import time
import json
import logging
import requests
from openai import OpenAI
# Import the full openai module for error handling
import openai
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
        try:
            self.scholarly_google = ScholarlyGoogle(
                timeout=timeout,
                max_retries=max_retries,
                base_delay=base_delay
            )
        except Exception as e:
            logger.error(f"Error initializing ScholarlyGoogle: {str(e)}")
            self.scholarly_google = None
        
        # Fall back to SerpAPI if API key is provided
        self.google_scholar = None
        if self.api_key:
            try:
                self.google_scholar = GoogleScholar(
                    api_key=self.api_key,
                    timeout=timeout,
                    max_retries=max_retries,
                    base_delay=base_delay
                )
            except Exception as e:
                logger.error(f"Error initializing GoogleScholar: {str(e)}")
                self.google_scholar = None
            
        # Initialize OpenAI client for compatibility with existing code
        # OpenAI v1.0.0 doesn't support additional parameters
        try:
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", "")
                # No other parameters should be passed here
            )
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
        
    @property
    def chat(self):
        """Get the chat completions interface."""
        if not self.client:
            logger.error("OpenAI client is not available, cannot access chat")
            raise ValueError("OpenAI client not initialized")
        return self.client.chat
        
    def chat_completions_create(self, **kwargs):
        """Create a chat completion with OpenAI API."""
        # Check if client was properly initialized
        if not self.client:
            logger.error("OpenAI client is not available, chat completion request failed")
            raise ValueError("OpenAI client not initialized")
            
        # Remove any parameters not supported by OpenAI v1.0.0
        if 'proxies' in kwargs:
            kwargs.pop('proxies')
        if 'request_timeout' in kwargs:
            kwargs.pop('request_timeout')
        if 'request_id' in kwargs:
            kwargs.pop('request_id')
        if 'retry' in kwargs:
            kwargs.pop('retry')
        
        try:    
            # Use the v1.0.0 API format
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise
        
    def chat_completions(self):
        """Get the chat completions interface."""
        if not self.client:
            logger.error("OpenAI client is not available, cannot access chat completions")
            raise ValueError("OpenAI client not initialized")
        return self.client.chat.completions
        
    def search_papers(self, query, max_results=10, timeout=None):
        """Search for academic papers using Google Scholar.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            timeout: Custom timeout for the search request (overrides default)
            
        Returns:
            Dictionary containing search results
        """
        try:
            # Apply timeout if provided
            search_timeout = timeout or self.timeout
            
            # First try using the scholarly library (no API key needed)
            if self.scholarly_google:
                try:
                    logger.info(f"Trying to search papers using scholarly with timeout={search_timeout}s")
                    # Note: scholarly doesn't support timeout parameter, so we can't pass it
                    results = self.scholarly_google.search(query, max_results=max_results)
                    if results.get('papers'):
                        return results
                except Exception as e:
                    logger.warning(f"Scholarly search failed: {str(e)}. Trying alternative method...")
            else:
                logger.warning("ScholarlyGoogle client is not available, skipping this search method")
            
            # If scholarly fails and we have an API key, try using SerpAPI
            if self.google_scholar:
                logger.info(f"Trying to search papers using SerpAPI with timeout={search_timeout}s")
                # Override the timeout for faster failure
                self.google_scholar.timeout = search_timeout
                results = self.google_scholar.search(query, max_results=max_results)
                return results
            else:
                logger.warning("No Google Scholar API client available")
                return {
                    "papers": [],
                    "error": "No working Google Scholar search method available",
                    "query": query,
                    "timestamp": time.time(),
                    "source": "google_scholar_not_available"
                }
                
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