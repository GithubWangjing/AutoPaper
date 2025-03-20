import markdown
import hashlib
import json
import os
from datetime import datetime, timedelta

def convert_markdown_to_html(markdown_text):
    """Convert markdown text to HTML."""
    try:
        html = markdown.markdown(markdown_text)
        return html
    except Exception as e:
        print(f"转换Markdown时出错: {str(e)}")
        return f"<p>Markdown转换错误: {str(e)}</p><pre>{markdown_text}</pre>"

def validate_paper_structure(paper):
    """Validate the structure of the generated paper."""
    required_sections = ['abstract', 'introduction', 'methodology', 'results', 'conclusion']
    paper_lower = paper.lower()
    
    missing_sections = [
        section for section in required_sections 
        if section not in paper_lower
    ]
    
    if missing_sections:
        raise ValueError(f"Missing required sections: {', '.join(missing_sections)}")
    
    return True

# 简单的内存缓存系统
class ResponseCache:
    def __init__(self):
        self.cache = {}
        
    def get(self, messages, model):
        cache_key = self._make_cache_key(messages, model)
        return self.cache.get(cache_key)
    
    def set(self, messages, model, response):
        cache_key = self._make_cache_key(messages, model)
        self.cache[cache_key] = response
    
    def _make_cache_key(self, messages, model):
        # 创建一个基于消息内容和模型的唯一键
        message_str = json.dumps([m.get('content', '') for m in messages])
        return f"{model}:{message_str}"

# 初始化全局缓存
response_cache = ResponseCache()

def format_timestamp(timestamp=None):
    """格式化时间戳为可读格式。"""
    if timestamp is None:
        timestamp = datetime.now()
    elif isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            return timestamp
    
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def safe_json_loads(json_string, default=None):
    """安全地解析JSON字符串，如果失败则返回默认值。"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
