import os
import json
import time
import logging
import random
from datetime import datetime
from scholarly import scholarly

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScholarlyGoogle:
    """Client for Google Scholar search using the scholarly library (no API key required)."""
    
    def __init__(self, timeout=30, max_retries=3, base_delay=1.0):
        """Initialize the Google Scholar client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Configure scholarly to not use proxies to avoid compatibility issues with OpenAI 1.0.0
        try:
            scholarly.use_proxy(None, None)
        except Exception as e:
            logger.warning(f"Failed to configure proxy settings for scholarly: {str(e)}")
        
    def search(self, query, max_results=10):
        """Search Google Scholar for academic papers on a topic.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        logger.info(f"Searching Google Scholar for: {query}")
        
        # Make request with retries
        for attempt in range(self.max_retries):
            try:
                # Search for the query
                search_query = scholarly.search_pubs(query)
                
                # Collect results
                papers = []
                count = 0
                
                # Get the specified number of results
                for result in search_query:
                    if count >= max_results:
                        break
                        
                    # Extract data
                    title = result.get('bib', {}).get('title', 'Unknown Title')
                    authors = result.get('bib', {}).get('author', ['Unknown Author'])
                    abstract = result.get('bib', {}).get('abstract', 'No abstract available')
                    url = result.get('pub_url', '')
                    year = result.get('bib', {}).get('pub_year', datetime.now().year)
                    citations = result.get('num_citations', 0)
                    
                    # Create a paper object
                    paper = {
                        'title': title,
                        'authors': authors,
                        'summary': abstract,
                        'url': url,
                        'published': str(year),
                        'citations': citations
                    }
                    
                    papers.append(paper)
                    count += 1
                    
                    # Add a small delay between fetches to avoid rate limiting
                    time.sleep(random.uniform(1.0, 2.0))
                
                # Return formatted results
                logger.info(f"Found {len(papers)} papers on Google Scholar using scholarly")
                return {
                    "papers": papers,
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "source": "google_scholar_scholarly"
                }
                
            except Exception as e:
                logger.error(f"Google Scholar search with scholarly failed (attempt {attempt+1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {sleep_time} seconds before retry")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Max retries exceeded for Google Scholar scholarly search")
                    raise
        
        # This should not be reached unless there's a logic error
        return {"papers": [], "error": "Failed to search Google Scholar"} 