import os
import time
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from openai import OpenAI
from openai import RateLimitError, APIError, APITimeoutError
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Arxiv:
    def __init__(self, timeout=30, max_retries=3, base_delay=1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.base_url = "http://export.arxiv.org/api/query"
        
    def search(self, query, max_results=10, sort_by="relevance", timeout=None):
        """Search ArXiv for papers."""
        timeout = timeout or self.timeout
        
        # 日志记录搜索查询
        logger.info(f"Searching arXiv for: {query}")
        
        # 如果查询是中文，生成附加的英文查询版本
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in query)
        if is_chinese:
            logger.info("Detected Chinese query, attempting to enhance search...")
            
            # 尝试使用一些相关关键词扩展
            # 对于医学领域的查询，添加一些特定的英文术语
            medical_keywords = ["medicine", "medical", "health", "clinical", "treatment", "diagnosis",
                               "orthopedics", "orthopedic", "bone", "joint", "surgery", "trauma"]
            ai_keywords = ["artificial intelligence", "machine learning", "deep learning", "neural network",
                          "large language model", "LLM", "transformer", "AI", "algorithm"]
            
            # 将原始查询与相关英文关键词组合
            combined_query = query
            
            # 检查是否包含"骨科"相关关键词
            if "骨科" in query:
                combined_query = f"(orthopedics OR orthopedic) OR ((bone OR joint) AND (AI OR model))"
                logger.info(f"Enhanced orthopedic query: {combined_query}")
                
            # 检查是否包含"大模型"相关关键词
            elif "大模型" in query or "模型" in query:
                combined_query = f"(large language model OR LLM OR deep learning model OR AI model OR large model)"
                logger.info(f"Enhanced model query: {combined_query}")
                
            # 检查是否包含"麻醉"相关关键词
            elif "麻醉" in query:
                combined_query = f"(anesthesia OR anesthetic OR anesthesiology) AND (AI OR model OR machine learning)"
                logger.info(f"Enhanced anesthesia query: {combined_query}")
                
            # 其他中文查询的通用处理
            else:
                # 创建一个基本的英文版本 (实际应用中可以接入翻译API)
                basic_english = query.replace("大模型", "large model").replace("骨科", "orthopedics").replace("麻醉", "anesthesia")
                combined_query = f"({basic_english})"
                logger.info(f"Added basic English translation: {combined_query}")
                
            # 使用增强的查询
            query = combined_query
        
        # Convert sort parameter to ArXiv format
        sort_map = {
            "relevance": "relevance",
            "lastUpdatedDate": "lastUpdatedDate",
            "submittedDate": "submittedDate"
        }
        sort_param = sort_map.get(sort_by, "relevance")
        
        # Prepare the query
        encoded_query = quote(query)
        
        # Construct URL
        url = f"{self.base_url}?search_query=all:{encoded_query}&start=0&max_results={max_results}&sortBy={sort_param}"
        logger.info(f"ArXiv API URL: {url}")
        
        # Enhanced error handling with retries
        for attempt in range(self.max_retries):
            try:
                logger.info(f"ArXiv API request attempt {attempt+1}/{self.max_retries}")
                response = requests.get(url, timeout=timeout)
                
                if response.status_code == 200:
                    results = self._parse_arxiv_response(response.text)
                    logger.info(f"Found {len(results['papers'])} papers on arXiv")
                    
                    # If no papers found but we have retries left, try again with a different query
                    if len(results['papers']) == 0 and attempt < self.max_retries - 1:
                        logger.warning("No papers found, will retry with a modified query")
                        
                        # Simplify the query if needed
                        if " AND " in query:
                            query = query.split(" AND ")[0]
                            encoded_query = quote(query)
                            url = f"{self.base_url}?search_query=all:{encoded_query}&start=0&max_results={max_results}&sortBy={sort_param}"
                            logger.info(f"Simplified query for next attempt: {query}")
                            time.sleep(self.base_delay * (attempt + 1))  # Exponential backoff
                            continue
                    
                    return results
                elif response.status_code == 429:
                    # Rate limited
                    logger.warning(f"ArXiv rate limit reached (attempt {attempt+1})")
                    wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                elif response.status_code >= 500:
                    # Server error
                    logger.warning(f"ArXiv server error {response.status_code} (attempt {attempt+1})")
                    wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                else:
                    # Other error
                    logger.error(f"ArXiv API error: {response.status_code}")
                    break
            except requests.exceptions.Timeout:
                logger.warning(f"ArXiv API timeout (attempt {attempt+1})")
                wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                logger.error(f"ArXiv API request error: {str(e)} (attempt {attempt+1})")
                wait_time = self.base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error in ArXiv API request: {str(e)} (attempt {attempt+1})")
                break
        
        # If we got here, all attempts failed
        logger.error(f"All {self.max_retries} ArXiv API attempts failed")
        raise APIError(f"ArXiv API failed after {self.max_retries} attempts")
                    
    def _parse_arxiv_response(self, content):
        """Parse the XML response from ArXiv."""
        try:
            root = ET.fromstring(content)
            
            # Extract namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'}
            
            papers = []
            for entry in root.findall('./atom:entry', ns):
                try:
                    # Get basic metadata
                    title = entry.find('./atom:title', ns)
                    title_text = title.text.strip() if title is not None and title.text else "Untitled"
                    
                    summary = entry.find('./atom:summary', ns)
                    summary_text = summary.text.strip() if summary is not None and summary.text else "No summary available"
                    
                    published = entry.find('./atom:published', ns)
                    published_text = published.text if published is not None and published.text else None
                    
                    updated = entry.find('./atom:updated', ns)
                    updated_text = updated.text if updated is not None and updated.text else None
                    
                    # Get authors
                    authors = []
                    for author in entry.findall('./atom:author/atom:name', ns):
                        if author.text:
                            authors.append(author.text)
                    
                    # Get links and ID
                    links = {}
                    for link in entry.findall('./atom:link', ns):
                        link_title = link.get('title', '')
                        link_href = link.get('href', '')
                        link_type = link.get('type', '')
                        
                        if link_title == 'pdf':
                            links['pdf'] = link_href
                        elif link_type == 'text/html':
                            links['html'] = link_href
                    
                    paper_id_elem = entry.find('./atom:id', ns)
                    paper_id = "unknown"
                    if paper_id_elem is not None and paper_id_elem.text:
                        paper_id = paper_id_elem.text
                        if '/' in paper_id:
                            paper_id = paper_id.split('/')[-1]
                            if 'v' in paper_id:
                                paper_id = paper_id.split('v')[0]
                    
                    # Get categories/topics
                    categories = []
                    for category in entry.findall('./atom:category', ns):
                        cat_term = category.get('term')
                        if cat_term:
                            categories.append(cat_term)
                    
                    # Get DOI if available
                    doi = None
                    for link in entry.findall('./atom:link', ns):
                        if link.get('title') == 'doi':
                            doi = link.get('href')
                    
                    # 格式化为更友好的对象
                    paper = {
                        'paper_id': paper_id,
                        'title': title_text,
                        'summary': summary_text,
                        'authors': authors,
                        'published': published_text[:10] if published_text else None,  # 只保留日期部分
                        'updated': updated_text[:10] if updated_text else None,  # 只保留日期部分
                        'url': links.get('html') or f"https://arxiv.org/abs/{paper_id}",  # 确保总是有URL
                        'pdf_url': links.get('pdf'),
                        'categories': categories,
                        'doi': doi,
                        'source': 'arxiv'
                    }
                    papers.append(paper)
                except Exception as e:
                    logger.error(f"Error parsing paper entry: {str(e)}")
                    continue
            
            return {
                'papers': papers,
                'total_results': len(papers)
            }
        except ET.ParseError as e:
            logger.error(f"XML parse error: {str(e)}")
            logger.error(f"Content: {content[:100]}...")  # Log the first 100 chars
            return {
                'papers': [],
                'total_results': 0,
                'error': f"XML parse error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error parsing arXiv response: {str(e)}")
            return {
                'papers': [],
                'total_results': 0,
                'error': f"Error parsing response: {str(e)}"
            } 