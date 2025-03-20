import os
import json
import time
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleScholar:
    """Client for Google Scholar search API using SerpAPI."""
    
    def __init__(self, api_key=None, timeout=30, max_retries=1, base_delay=1.0):
        """Initialize the Google Scholar API client.
        
        Args:
            api_key: SerpAPI key (optional, will use SERPAPI_KEY from env if not provided)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts (default: 1)
            base_delay: Base delay between retries in seconds
        """
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.base_url = "https://serpapi.com/search"
        
    def search(self, query, max_results=10):
        """Search Google Scholar for academic papers on a topic.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        logger.info(f"Searching Google Scholar for: {query}")
        
        if not self.api_key:
            raise ValueError("SerpAPI key is required for Google Scholar search")
        
        # Prepare parameters for Google Scholar search
        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.api_key,
            "num": min(max_results, 20),  # SerpAPI has a limit
            "as_ylo": datetime.now().year - 5  # Papers from last 5 years
        }
        
        # Make request with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Format the results
                papers = []
                
                # Process organic results
                if "organic_results" in data:
                    for result in data["organic_results"]:
                        paper = {
                            "title": result.get("title", "Unknown Title"),
                            "authors": self._extract_authors(result),
                            "summary": result.get("snippet", "No summary available"),
                            "url": result.get("link", ""),
                            "published": self._extract_publication_date(result),
                            "citations": result.get("cited_by", {}).get("total", 0)
                        }
                        papers.append(paper)
                
                # Return formatted results
                logger.info(f"Found {len(papers)} papers on Google Scholar")
                return {
                    "papers": papers,
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "source": "google_scholar"
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Google Scholar API request failed (attempt {attempt+1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Max retries exceeded for Google Scholar search")
                    raise
        
        # This should not be reached unless there's a logic error
        return {"papers": [], "error": "Failed to search Google Scholar"}
    
    def _extract_authors(self, result):
        """Extract author information from a search result."""
        # Try to get publication info which might contain authors
        publication_info = result.get("publication_info", {})
        
        # Extract author names from summary and publication info
        authors = []
        
        # Usually authors are in the publication_info or can be parsed from snippet
        if "authors" in publication_info:
            authors = publication_info["authors"]
        elif "summary" in publication_info:
            # Try to extract author names from summary
            summary = publication_info["summary"]
            if "," in summary:
                authors = [author.strip() for author in summary.split(",")]
        
        # If no authors were found, use a placeholder
        if not authors:
            authors = ["Unknown Author"]
            
        return authors
    
    def _extract_publication_date(self, result):
        """Extract publication date from a search result."""
        # Try to get year from publication info
        publication_info = result.get("publication_info", {})
        
        # Check if we have a publication year
        if "year" in publication_info:
            return str(publication_info["year"])
        
        # If we don't have publication info, use current year
        return str(datetime.now().year) 