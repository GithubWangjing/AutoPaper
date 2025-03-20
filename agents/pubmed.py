import os
import time
import json
import logging
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubMed:
    """Client for searching academic papers on PubMed."""
    
    def __init__(self, timeout=30, max_retries=3, base_delay=1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.search_url = f"{self.base_url}/esearch.fcgi"
        self.summary_url = f"{self.base_url}/esummary.fcgi"
        self.fetch_url = f"{self.base_url}/efetch.fcgi"
        
    def search(self, query, max_results=10, timeout=None):
        """Search PubMed for papers related to the query."""
        timeout = timeout or self.timeout
        logger.info(f"Searching PubMed for: {query}")
        
        # If query is in Chinese, try to enhance it for better results
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in query)
        if is_chinese:
            query = self._enhance_chinese_query(query)
            
        # Encode the query for URL
        encoded_query = quote(query)
        
        # Get paper IDs matching the query
        try:
            paper_ids = self._search_paper_ids(encoded_query, max_results, timeout)
            if not paper_ids:
                logger.warning(f"No paper IDs found for query: {query}")
                return {
                    'papers': [],
                    'total_results': 0,
                    'query': query,
                    'timestamp': time.time(),
                    'source': 'pubmed'
                }
                
            # Get details for each paper ID
            papers = self._fetch_paper_details(paper_ids, timeout)
            
            return {
                'papers': papers,
                'total_results': len(papers),
                'query': query,
                'timestamp': time.time(),
                'source': 'pubmed'
            }
        except Exception as e:
            logger.error(f"Error searching PubMed: {str(e)}")
            return {
                'papers': [],
                'total_results': 0,
                'error': str(e),
                'query': query,
                'timestamp': time.time(),
                'source': 'pubmed_error'
            }
    
    def _enhance_chinese_query(self, query):
        """Enhance Chinese query for better results in PubMed."""
        # Map of common Chinese medical terms to English equivalents
        term_map = {
            "骨科": "orthopedics",
            "大模型": "large language model",
            "模型": "model",
            "麻醉": "anesthesia",
            "人工智能": "artificial intelligence",
            "机器学习": "machine learning",
            "深度学习": "deep learning"
        }
        
        enhanced_query = query
        for cn_term, en_term in term_map.items():
            if cn_term in query:
                enhanced_query = enhanced_query.replace(cn_term, en_term)
                
        logger.info(f"Enhanced PubMed query: {enhanced_query}")
        return enhanced_query
        
    def _search_paper_ids(self, query, max_results, timeout):
        """Search PubMed and get paper IDs."""
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        # Try with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"PubMed search attempt {attempt+1}/{self.max_retries}")
                response = requests.get(self.search_url, params=search_params, timeout=timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    paper_ids = data.get('esearchresult', {}).get('idlist', [])
                    logger.info(f"Found {len(paper_ids)} paper IDs on PubMed")
                    return paper_ids
                    
                elif response.status_code == 429:
                    # Rate limited
                    logger.warning(f"PubMed rate limit reached (attempt {attempt+1})")
                    wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                    
                else:
                    # Other error
                    logger.error(f"PubMed API error: {response.status_code}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.base_delay * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        break
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"PubMed API request error: {str(e)} (attempt {attempt+1})")
                if attempt < self.max_retries - 1:
                    wait_time = self.base_delay * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    break
                    
        # If we got here, all attempts failed
        logger.error(f"All {self.max_retries} PubMed search attempts failed")
        return []
        
    def _fetch_paper_details(self, paper_ids, timeout):
        """Fetch details for paper IDs from PubMed."""
        if not paper_ids:
            return []
            
        # Convert list of IDs to comma-separated string
        id_string = ','.join(paper_ids)
        
        # Prepare parameters for summary request
        fetch_params = {
            'db': 'pubmed',
            'id': id_string,
            'retmode': 'xml',
            'rettype': 'abstract'
        }
        
        papers = []
        try:
            response = requests.get(self.fetch_url, params=fetch_params, timeout=timeout)
            
            if response.status_code == 200:
                xml_data = response.text
                papers = self._parse_pubmed_xml(xml_data)
                return papers
            else:
                logger.error(f"PubMed fetch error: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"PubMed fetch request error: {str(e)}")
            return []
            
    def _parse_pubmed_xml(self, xml_data):
        """Parse PubMed XML response into structured paper data."""
        papers = []
        try:
            root = ET.fromstring(xml_data)
            article_elements = root.findall('.//PubmedArticle')
            
            for article in article_elements:
                try:
                    # Extract basic metadata
                    pmid = article.find('.//PMID').text
                    article_element = article.find('.//Article')
                    
                    # Title
                    title_element = article_element.find('.//ArticleTitle')
                    title = title_element.text if title_element is not None else "Untitled"
                    
                    # Abstract
                    abstract_element = article_element.find('.//AbstractText')
                    abstract = abstract_element.text if abstract_element is not None else ""
                    
                    # Authors
                    author_elements = article_element.findall('.//Author')
                    authors = []
                    
                    for author in author_elements:
                        lastname = author.find('.//LastName')
                        forename = author.find('.//ForeName')
                        
                        if lastname is not None and forename is not None:
                            author_name = f"{forename.text} {lastname.text}"
                            authors.append(author_name)
                        elif lastname is not None:
                            authors.append(lastname.text)
                            
                    # Journal
                    journal_element = article_element.find('.//Journal/Title')
                    journal = journal_element.text if journal_element is not None else "Unknown Journal"
                    
                    # Year
                    year_element = article_element.find('.//PubDate/Year')
                    year = year_element.text if year_element is not None else "Unknown Year"
                    
                    # URL
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    
                    # Create paper object
                    paper = {
                        'title': title,
                        'authors': authors,
                        'abstract': abstract,
                        'url': url,
                        'journal': journal,
                        'year': year,
                        'id': pmid,
                        'source': 'pubmed'
                    }
                    
                    papers.append(paper)
                    
                except Exception as e:
                    logger.error(f"Error parsing individual PubMed article: {str(e)}")
                    continue
                    
            return papers
            
        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {str(e)}")
            return [] 