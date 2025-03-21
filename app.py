import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, send_file, send_from_directory
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from agents.review_agent import ReviewAgent
from agents.supervisor_agent import SupervisorAgent
from agents.communication_agent import CommunicationAgent
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import markdown2
from io import BytesIO
import traceback
import re
import html
import threading

# Load environment variables
load_dotenv()

# Configure scholarly to not use proxies (must be done before any other imports)
try:
    from scholarly import scholarly
    scholarly.use_proxy(None, None)
    logging.info("Configured scholarly to not use proxies")
except Exception as e:
    logging.warning(f"Failed to configure scholarly proxy settings: {str(e)}")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "default_secret_key")

# Application configuration
APP_CONFIG = {
    'ENABLE_MULTI_AGENT': os.environ.get('ENABLE_MULTI_AGENT', 'true').lower() == 'true',
    'DEFAULT_MODEL_TYPE': os.environ.get('DEFAULT_MODEL_TYPE', 'siliconflow'),
    'DEFAULT_RESEARCH_SOURCE': os.environ.get('DEFAULT_RESEARCH_SOURCE', 'arxiv')
}

# Make configuration available to templates
@app.context_processor
def inject_app_config():
    return {'app_config': APP_CONFIG}

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI", 'sqlite:///instance/paper_projects.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import and add figure generator functions to the template context
try:
    from utils.figure_generator import line_plot, bar_plot, scatter_plot, figure_to_base64
    
    @app.context_processor
    def inject_figure_utils():
        """Add figure generator functions to template context"""
        return {
            'line_plot': line_plot,
            'bar_plot': bar_plot,
            'scatter_plot': scatter_plot,
            'figure_to_base64': figure_to_base64
        }
    logging.info("Figure generator functions added to template context")
except ImportError:
    logging.warning("Figure generator module not found, visualization functions will not be available")
except Exception as e:
    logging.error(f"Error setting up figure generator: {str(e)}")

# Add custom Jinja2 filters
@app.template_filter('fromjson')
def fromjson_filter(value):
    """Convert a JSON string to a Python object.
    
    This template filter is critical for the application as it allows the templates
    to convert JSON strings stored in the database into Python dictionaries/objects
    that can be used in the templates. Without this filter, the templates would not
    be able to access the structured data from research results, paper drafts, etc.
    
    Example usage in a template:
    {% set research_data = research.content|fromjson %}
    {{ research_data.papers|length }}
    
    Args:
        value: JSON string to convert, or a Python object to pass through
        
    Returns:
        Python object (dict, list, etc.) if conversion successful,
        the original value if it's already a Python object,
        or an empty dict if there was an error parsing the JSON
    """
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value  # Already a Python object
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return {}  # Return empty dict on error

@app.template_filter('process_academic_content')
def process_academic_content(content):
    """Process academic content to enhance formatting, supporting markdown and LaTeX.
    
    This function enhances academic content with:
    1. Proper Markdown rendering if content is in markdown format
    2. LaTeX equations properly formatted for MathJax
    
    Args:
        content: The content to process, typically a paper draft or research content
        
    Returns:
        Formatted HTML content ready for display
    """
    if not content:
        return ""
    
    try:
        # Check if the content contains Markdown-like syntax
        markdown_indicators = ['#', '##', '###', '```', '*', '1.', '- ', '[', '](', '|']
        is_markdown = any(indicator in content for indicator in markdown_indicators)
        
        # If it's likely markdown, use markdown processing
        if is_markdown:
            # If markdown package is available, use it for better formatting
            try:
                import markdown
                
                # 处理中文内容的特殊情况，确保段落正确换行
                # 替换单个换行为真正的换行
                content = re.sub(r'(?<!\n)\n(?!\n)', '\n\n', content)
                
                # 处理标题前后的空格问题
                content = re.sub(r'(#+)([^\n#])', r'\1 \2', content)
                
                html_content = markdown.markdown(
                    content,
                    extensions=[
                        'markdown.extensions.extra',
                        'markdown.extensions.codehilite',
                        'markdown.extensions.tables'
                    ]
                )
                
                # 处理数学公式
                html_content = re.sub(r'\$\$(.*?)\$\$', r'\\[\1\\]', html_content, flags=re.DOTALL)
                html_content = re.sub(r'\$(.*?)\$', r'\\(\1\\)', html_content)
                
                return html_content
            
            except ImportError:
                # Fallback to basic HTML with newlines for paragraphs
                # Escape HTML entities, then convert newlines to paragraphs
                escaped_content = html.escape(content)
                paragraphs = escaped_content.split('\n\n')
                formatted_paragraphs = []
                for p in paragraphs:
                    if p.strip():
                        # 使用r-string和+组合避免f-string中反斜杠的问题
                        formatted_paragraphs.append('<p>' + p.replace('\n', '<br>') + '</p>')
                
                html_content = '\n'.join(formatted_paragraphs)
                return html_content
        
        # For plain text content
        else:
            # Simple conversion for non-markdown content
            # Escape HTML entities, then convert newlines to paragraphs
            escaped_content = html.escape(content)
            paragraphs = escaped_content.split('\n\n')
            formatted_paragraphs = []
            for p in paragraphs:
                if p.strip():
                    # 使用r-string和+组合避免f-string中反斜杠的问题
                    formatted_paragraphs.append('<p>' + p.replace('\n', '<br>') + '</p>')
            
            html_content = '\n'.join(formatted_paragraphs)
            return html_content
            
    except Exception as e:
        print(f"Error processing content: {str(e)}")
        return f"<p>Error processing content: {str(e)}</p><pre>{content}</pre>"

# Initialize SQLAlchemy with app
db = SQLAlchemy(app)

# Initialize agents with the default model 
model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")

# Cache for agent instances
_agent_cache = {}

# 日志缓存，记录每个项目的代理工作日志
project_logs = {}

# Global dictionaries to store logs and data
agent_logs = {}  # Store agent logs for interactive multi-agent processes

# 添加日志记录器
def log_agent_activity(project_id, agent_type, activity, details=None):
    """记录代理活动到项目日志中"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'agent_type': agent_type,
        'activity': activity,
        'details': details
    }
    
    if project_id not in project_logs:
        project_logs[project_id] = []
    
    project_logs[project_id].append(log_entry)
    
    # 保持日志长度，避免内存泄漏
    if len(project_logs[project_id]) > 100:
        project_logs[project_id] = project_logs[project_id][-100:]
    
    # 同时打印到服务器日志
    logger.info(f"[Project {project_id}] {agent_type}: {activity}")

# 定义数据模型
class PaperProject(db.Model):
    """项目数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default="created")
    model_type = db.Column(db.String(50), default="siliconflow")
    research_source = db.Column(db.String(50), default="none")
    paper_type = db.Column(db.String(50), default="regular")
    language = db.Column(db.String(10), default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Custom model properties
    custom_model_endpoint = db.Column(db.String(255), nullable=True)
    custom_model_api_key = db.Column(db.String(255), nullable=True)
    custom_model_name = db.Column(db.String(100), nullable=True)
    custom_model_temperature = db.Column(db.Float, default=0.7, nullable=True)
    custom_model_max_tokens = db.Column(db.Integer, default=2000, nullable=True)
    
    # 关联版本
    versions = db.relationship('PaperVersion', backref='project', lazy=True)
    
    # 关联消息
    messages = db.relationship('AgentMessage', backref='project', lazy=True)

class PaperVersion(db.Model):
    """论文版本数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('paper_project.id'), nullable=False)
    version_number = db.Column(db.Integer, default=1)
    content_type = db.Column(db.String(50), default="research") # research, draft, review, final
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AgentMessage(db.Model):
    """代理消息数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('paper_project.id'), nullable=False)
    agent_type = db.Column(db.String(50))
    message_type = db.Column(db.String(50), default="info") # info, warning, error
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 创建数据库表
with app.app_context():
    db.create_all()

def get_agent_for_project(project, agent_type):
    """创建并返回一个项目专用的代理实例
    
    Args:
        project: 项目实例
        agent_type: 代理类型 (research, writing, review)
    
    Returns:
        代理实例
    """
    model_type = project.model_type
    
    # 如果是自定义模型，创建配置字典
    custom_model_config = None
    if model_type == 'custom':
        custom_model_config = {}
        # Safely get custom model properties
        if hasattr(project, 'custom_model_endpoint'):
            custom_model_config['endpoint'] = project.custom_model_endpoint
        if hasattr(project, 'custom_model_api_key'):
            custom_model_config['api_key'] = project.custom_model_api_key
        if hasattr(project, 'custom_model_name'):
            custom_model_config['model_name'] = project.custom_model_name
        if hasattr(project, 'custom_model_temperature'):
            custom_model_config['temperature'] = project.custom_model_temperature
        if hasattr(project, 'custom_model_max_tokens'):
            custom_model_config['max_tokens'] = project.custom_model_max_tokens
    
    # 根据代理类型创建相应的代理
    if agent_type == 'research':
        research_source = project.research_source
        return ResearchAgent(model_type=model_type, 
                             research_source=research_source,
                             custom_model_config=custom_model_config)
    elif agent_type == 'writing':
        return WritingAgent(model_type=model_type,
                           custom_model_config=custom_model_config)
    elif agent_type == 'review':
        return ReviewAgent(model_type=model_type,
                          custom_model_config=custom_model_config)
    elif agent_type == 'supervisor':
        return SupervisorAgent(model_type=model_type,
                              custom_model_config=custom_model_config)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

def get_research_agent(research_source=None):
    """Create and return a research agent.
    
    Args:
        research_source: Research source to use (arxiv, google_scholar, or none)
            If None, uses the default from environment variables
    """
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    
    # If research_source is not specified, use default from environment
    if research_source is None:
        research_source = os.getenv("DEFAULT_RESEARCH_SOURCE", "arxiv")
        
    return ResearchAgent(model_type=model_type, research_source=research_source)

def get_writing_agent():
    """Create and return a writing agent."""
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    return WritingAgent(model_type=model_type)

def get_review_agent():
    """Create and return a review agent."""
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    return ReviewAgent(model_type=model_type)

def get_supervisor_agent():
    """Create and return a supervisor agent."""
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    return SupervisorAgent(model_type=model_type)

# Valid configuration options
VALID_MODEL_TYPES = ['openai', 'siliconflow']

@app.route('/')
def index():
    """Main landing page showing projects."""
    with app.app_context():
        projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    data = request.json
    topic = data.get('topic', '')
    model_type = data.get('model_type', 'siliconflow')
    research_source = data.get('research_source', 'none')
    paper_type = data.get('paper_type', 'regular')
    language = data.get('language', 'en')
    
    # 验证自定义模型设置
    custom_model_endpoint = None
    custom_model_api_key = None
    custom_model_name = None
    custom_model_temperature = 0.7
    custom_model_max_tokens = 2000
    
    if model_type == 'custom':
        custom_model_endpoint = data.get('custom_model_endpoint', '')
        custom_model_api_key = data.get('custom_model_api_key', '')
        custom_model_name = data.get('custom_model_name', '')
        custom_model_temperature = float(data.get('custom_model_temperature', 0.7))
        custom_model_max_tokens = int(data.get('custom_model_max_tokens', 2000))
        
        if not custom_model_endpoint or not custom_model_api_key:
            return jsonify({'error': 'Custom model settings are incomplete'}), 400

    # 创建项目
    project = PaperProject(
        topic=topic, 
        model_type=model_type,
        research_source=research_source,
        paper_type=paper_type, 
        language=language,
        custom_model_endpoint=custom_model_endpoint,
        custom_model_api_key=custom_model_api_key,
        custom_model_name=custom_model_name,
        custom_model_temperature=custom_model_temperature,
        custom_model_max_tokens=custom_model_max_tokens
    )
    
    db.session.add(project)
    db.session.commit()
    
    # 记录日志
    log_agent_activity(project.id, "system", "project_created", 
                      {"topic": topic, "model": model_type, 
                       "research_source": research_source,
                       "paper_type": paper_type,
                       "language": language})
    
    return jsonify({
        'id': project.id,
        'topic': project.topic,
        'status': project.status,
        'model_type': project.model_type,
        'research_source': project.research_source,
        'paper_type': project.paper_type,
        'language': project.language,
        'created_at': project.created_at.isoformat()
    })

@app.route('/api/projects/<int:project_id>/logs', methods=['GET'])
def get_project_logs(project_id):
    """获取项目的实时日志"""
    try:
        # 获取指定时间戳之后的日志
        since_timestamp = request.args.get('since')
        
        if project_id in project_logs:
            logs = project_logs[project_id]
            
            # 如果指定了时间戳，只返回该时间戳之后的日志
            if since_timestamp:
                filtered_logs = []
                for log in logs:
                    # Ensure all log entries have the required fields
                    if not isinstance(log, dict):
                        continue
                    if 'timestamp' not in log:
                        continue
                    if log['timestamp'] > since_timestamp:
                        # Ensure log entry can be serialized to JSON
                        sanitized_log = {
                            'timestamp': log.get('timestamp', ''),
                            'agent_type': log.get('agent_type', 'unknown'),
                            'activity': log.get('activity', ''),
                        }
                        
                        # Only add details if it's a simple type
                        details = log.get('details')
                        if details is not None:
                            if isinstance(details, (str, int, float, bool)) or details is None:
                                sanitized_log['details'] = details
                            elif isinstance(details, dict):
                                try:
                                    # Try to convert complex details to JSON string
                                    sanitized_log['details'] = json.dumps(details)
                                except:
                                    sanitized_log['details'] = str(details)
                            else:
                                sanitized_log['details'] = str(details)
                        
                        filtered_logs.append(sanitized_log)
                return jsonify(filtered_logs)
            else:
                # Sanitize all logs
                sanitized_logs = []
                for log in logs:
                    if not isinstance(log, dict):
                        continue
                    sanitized_log = {
                        'timestamp': log.get('timestamp', ''),
                        'agent_type': log.get('agent_type', 'unknown'),
                        'activity': log.get('activity', ''),
                    }
                    
                    # Only add details if it's a simple type
                    details = log.get('details')
                    if details is not None:
                        if isinstance(details, (str, int, float, bool)) or details is None:
                            sanitized_log['details'] = details
                        elif isinstance(details, dict):
                            try:
                                # Try to convert complex details to JSON string
                                sanitized_log['details'] = json.dumps(details)
                            except:
                                sanitized_log['details'] = str(details)
                        else:
                            sanitized_log['details'] = str(details)
                    
                    sanitized_logs.append(sanitized_log)
                return jsonify(sanitized_logs)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"Error getting project logs: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<int:project_id>', methods=['GET'])
def project_detail(project_id):
    """项目详情页面"""
    try:
        # 获取项目信息
        project = PaperProject.query.get(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('index'))
        
        # 获取论文版本
        versions = PaperVersion.query.filter_by(project_id=project_id).order_by(PaperVersion.created_at.desc()).all()
        
        # 获取当前草稿
        draft = None
        for version in versions:
            if version.content_type == 'draft':
                draft = version
                break
        
        # 如果有草稿，确保图片目录已设置
        if draft and 'figure' in draft.content.lower():
            try:
                # 尝试运行图片设置脚本，确保图片可以被正确显示
                from utils.setup_figures import copy_figures
                copy_figures('static/figures', 'figures')
                app.logger.info(f"Copied figures for project {project_id}")
            except Exception as e:
                app.logger.error(f"Error setting up figures for project {project_id}: {str(e)}")
        
        # 获取研究内容
        research = None
        for version in versions:
            if version.content_type == 'research':
                research = version
                break
        
        return render_template(
            'project_detail.html', 
            project=project, 
            versions=versions,
            draft=draft,
            research=research,
            paper_types=get_paper_types_dict(),
            languages=get_languages_dict()
        )
    except Exception as e:
        app.logger.error(f"Error getting project details: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

def get_paper_types_dict():
    """获取论文类型字典"""
    try:
        from utils.paper_types import get_paper_types
        return get_paper_types()
    except ImportError:
        return {"regular": {"name": "Regular Paper"}}

def get_languages_dict():
    """获取支持的语言字典"""
    try:
        from utils.paper_types import get_languages
        return get_languages()
    except ImportError:
        return {"en": {"name": "English"}}

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get all projects."""
    try:
        projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
        result = []
        for project in projects:
            # Convert comma-separated research_source to array for frontend
            research_sources = []
            if project.research_source and project.research_source != 'none':
                research_sources = [src.strip() for src in project.research_source.split(',')]
                
            result.append({
                'id': project.id,
                'topic': project.topic,
                'status': project.status,
                'model_type': project.model_type,
                'research_source': project.research_source,
                'research_sources': research_sources,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get a project by ID."""
    try:
        project = PaperProject.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found"}), 404
        
        # Get all versions for this project
        versions = PaperVersion.query.filter_by(project_id=project_id).all()
        versions_data = []
        for version in versions:
            versions_data.append({
                'id': version.id,
                'version_number': version.version_number,
                'content_type': version.content_type,
                'created_at': version.created_at.isoformat() if version.created_at else None
            })
        
        # Convert comma-separated research_source to array for frontend
        research_sources = []
        if project.research_source and project.research_source != 'none':
            research_sources = [src.strip() for src in project.research_source.split(',')]
            
        return jsonify({
            'id': project.id,
            'topic': project.topic,
            'status': project.status,
            'model_type': project.model_type,
            'research_source': project.research_source,
            'research_sources': research_sources,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'updated_at': project.updated_at.isoformat() if project.updated_at else None,
            'versions': versions_data
        })
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-research', methods=['POST'])
def api_start_research(project_id):
    """Start the research phase for a project."""
    try:
        project = PaperProject.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found"}), 404
        
        # Check if project is already in research phase
        if project.status in ["researching"]:
            logger.info(f"[Project {project_id}] Research already in progress")
            return jsonify({
                "status": "in_progress",
                "message": "Research already in progress"
            })
        
        # 更新项目状态
        project.status = "researching"
        db.session.commit()
        
        # 记录活动
        log_agent_activity(project_id, 'system', f'Starting research phase for topic: {project.topic}')
        
        # 异步执行研究任务
        # 在实际应用中应该使用Celery或其他异步任务队列
        # 这里为了简化，直接在请求中执行
        try:
            # 获取研究代理，使用项目指定的研究源
            research_agent = get_agent_for_project(project, 'research')
            
            # 记录活动
            log_agent_activity(project_id, 'research', f'Initializing research agent with source: {project.research_source}')
            
            # Check if research is already in progress (uses our new lock mechanism)
            response = research_agent.process(project.topic)
            
            # Check if we got an "in progress" message
            try:
                result_data = json.loads(response)
                if isinstance(result_data, dict) and result_data.get('status') == 'in_progress':
                    return jsonify({
                        "status": "in_progress",
                        "message": result_data.get('message', 'Research in progress')
                    })
            except:
                pass
                
            # 记录活动
            log_agent_activity(project_id, 'research', 'Research completed successfully')
            
            # 将研究结果存储为一个版本
            version = PaperVersion(
                project_id=project_id,
                version_number=1,
                content_type='research',
                content=response
            )
            db.session.add(version)
            
            # 更新项目状态
            project.status = "research_complete"
            db.session.commit()
            
            # 添加一条成功消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='research',
                message_type='info',
                message='Research completed successfully'
            )
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": "Research completed successfully"
            })
            
        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            
            # 添加一条错误消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='research',
                message_type='error',
                message=f'Error during research: {str(e)}'
            )
            db.session.add(message)
            
            # 更新项目状态
            project.status = "research_failed"
            db.session.commit()
            
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting research: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-writing', methods=['POST'])
def api_start_writing(project_id):
    """启动写作流程"""
    try:
        with app.app_context():
            # 获取项目信息
            project = PaperProject.query.get(project_id)
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            # 获取最新研究内容
            research_version = get_latest_version(project_id, 'research')
            if not research_version:
                return jsonify({'error': 'No research found for this project'}), 400
            
            research_content = research_version.content if research_version else ""
            
            # 获取论文模板
            try:
                from utils.template_generator import generate_paper_template
                template = generate_paper_template(
                    project.topic, 
                    paper_type_id=project.paper_type, 
                    language_id=project.language
                )
                log_agent_activity(project_id, "system", "template_generated", 
                                  {"paper_type": project.paper_type, "language": project.language})
            except ImportError:
                # 如果模板生成器不可用，使用简单模板
                template = f"# {project.topic}\n\n## Abstract\n\n## Introduction\n\n## Methods\n\n## Results\n\n## Discussion\n\n## Conclusion\n\n## References\n\n"
                log_agent_activity(project_id, "system", "using_default_template")
            
            # 获取写作代理
            writing_agent = get_agent_for_project(project, 'writing')
            if not writing_agent:
                return jsonify({'error': 'Failed to initialize writing agent'}), 500
            
            # 写作提示
            prompt = f"""
            You are an academic writing assistant. I want you to write a complete academic paper on the topic: "{project.topic}".
            
            Use the following research information:
            {research_content}
            
            Please follow this paper structure/template:
            {template}
            
            Additional guidelines:
            1. Write in a formal academic style appropriate for {project.language}
            2. Follow the structure exactly as provided
            3. Include citations where appropriate
            4. Create realistic and meaningful content based on the research
            5. The final paper should be comprehensive and ready for review
            6. Include placeholders for figures where appropriate (e.g., [Figure 1: Description])
            
            Please provide the complete paper in Markdown format.
            """
            
            # 启动写作任务
            project.status = "writing"
            db.session.commit()
            log_agent_activity(project_id, "writing", "writing_started")
            
            # 异步执行写作任务
            def async_write():
                try:
                    draft = writing_agent.generate(prompt)
                    save_version(project_id, 'draft', draft)
                    project.status = "draft_completed"
                    db.session.commit()
                    log_agent_activity(project_id, "writing", "writing_completed")
                except Exception as e:
                    project.status = "writing_failed"
                    db.session.commit()
                    log_agent_activity(project_id, "writing", "writing_failed", {"error": str(e)})
                    logger.error(f"Writing failed for project {project_id}: {str(e)}")
            
            threading.Thread(target=async_write).start()
            
            return jsonify({'status': 'success', 'message': 'Writing process started'})
    
    except Exception as e:
        logger.error(f"Error starting writing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-review', methods=['POST'])
def api_start_review(project_id):
    """Start the review process for a project."""
    try:
        # Get the project
        project = PaperProject.query.get_or_404(project_id)
        
        # Update project status
        project.status = 'reviewing'
        db.session.commit()
        
        # Log the start of the review
        logger.info(f"[Project {project_id}] review: Initializing review agent")
        
        # Get the review agent
        review_agent = get_agent_for_project(project, 'review')
        
        # Get the latest draft
        latest_draft = PaperVersion.query.filter_by(
            project_id=project_id,
            content_type='draft'
        ).order_by(PaperVersion.created_at.desc()).first()
        if not latest_draft:
            return jsonify({'error': 'No draft found for review'}), 400
            
        # Log the review process
        logger.info(f"[Project {project_id}] review: Reviewing paper on topic: {project.topic}")
        
        # Get review feedback
        feedback = review_agent.process(project.topic, latest_draft.content)
        
        # Ensure feedback is a string with proper Markdown formatting
        if isinstance(feedback, list):
            # If it's a list, join with newlines and ensure proper Markdown
            feedback_str = ""
            for item in feedback:
                if item.startswith('## '):
                    # It's already a heading
                    feedback_str += f"{item}\n\n"
                else:
                    # It's a bullet point
                    feedback_str += f"- {item}\n"
            feedback = feedback_str
        elif not isinstance(feedback, str):
            # Convert any other type to string and wrap in markdown
            feedback = f"## Review Feedback\n\n{str(feedback)}"
        
        # Save the review results
        try:
            save_version(project_id, 'review', feedback)
        except Exception as e:
            logger.error(f"Error during review: {str(e)}")
            return jsonify({'error': f'Error saving review: {str(e)}'}), 500
            
        # Update project status
        project.status = 'review_complete'
        db.session.commit()
        
        # Log completion
        logger.info(f"[Project {project_id}] review: Review completed successfully")
        
        return jsonify({'status': 'success', 'message': 'Review completed successfully'})
        
    except Exception as e:
        logger.error(f"Error starting review: {str(e)}")
        return jsonify({'error': f'Error starting review: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/start-multi-agent', methods=['POST'])
def api_start_multi_agent(project_id):
    """Start the multi-agent workflow for a project."""
    try:
        # 获取项目
        project = PaperProject.query.get_or_404(project_id)
        
        # 阻止重复处理
        if project.status == "completed":
            return jsonify({"error": "项目已完成"}), 400
        
        # 更新项目状态为处理中
        project.status = "processing"
        db.session.commit()
        
        # 记录开始多代理处理
        log_agent_activity(project_id, 'system', f'开始多代理协作流程：研究 → 写作 → 审阅 → 修订')
        
        # 阶段1：研究 - 获取相关论文和研究资料
        log_agent_activity(project_id, 'system', '阶段1：开始研究')
        research_agent = get_agent_for_project(project, 'research')
        
        # 记录进度
        log_agent_activity(project_id, 'research', f'开始收集与"{project.topic}"相关的论文')
        research_result = research_agent.process(project.topic)
            
        # 保存研究结果
        save_version(project_id, "research", research_result)
        log_agent_activity(project_id, 'research', '研究阶段完成，发现了相关论文')
        
        # 阶段2：写作 - 根据研究结果撰写初稿
        log_agent_activity(project_id, 'system', '阶段2：开始写作')
        writing_agent = get_agent_for_project(project, 'writing')
        
        log_agent_activity(project_id, 'writing', '根据研究结果撰写论文初稿')
        paper_draft = writing_agent.process(project.topic, research_result)
        
        # 保存初稿
        draft_version = save_version(project_id, "draft", paper_draft)
        log_agent_activity(project_id, 'writing', '论文初稿完成')
        
        # 阶段3：审阅 - 审阅初稿并提供修改建议
        log_agent_activity(project_id, 'system', '阶段3：开始审阅')
        review_agent = get_agent_for_project(project, 'review')
        
        log_agent_activity(project_id, 'review', '开始审阅论文初稿')
        review_feedback = review_agent.process(project.topic, paper_draft)
        
        # 将审阅反馈转换为JSON字符串进行存储 (如果还不是字符串)
        if not isinstance(review_feedback, str):
            review_feedback_str = json.dumps(review_feedback, ensure_ascii=False)
        else:
            review_feedback_str = review_feedback
            
        # 保存审阅结果
        review_version = save_version(project_id, "review", review_feedback_str)
        log_agent_activity(project_id, 'review', '审阅完成，生成反馈意见')
        
        # 阶段4：修订 - 根据审阅意见修改论文
        log_agent_activity(project_id, 'system', '阶段4：根据审阅意见修订论文')
        log_agent_activity(project_id, 'writing', '开始根据审阅意见修改论文')
        
        # 将审阅反馈传递给写作代理进行修订 (直接传递对象，不需要再次解析)
        final_paper = writing_agent.revise_draft(paper_draft, review_feedback)
        
        # 保存最终稿
        final_version = save_version(project_id, "final", final_paper)
        log_agent_activity(project_id, 'writing', '论文修订完成，生成最终稿')
        
        # 更新项目状态为已完成
        project.status = "completed"
        db.session.commit()
        
        log_agent_activity(project_id, 'system', '多代理协作流程完成')
        
        return jsonify({
            "status": "success",
            "research_id": get_latest_version_id(project_id, "research"),
            "draft_id": get_latest_version_id(project_id, "draft"),
            "review_id": get_latest_version_id(project_id, "review"),
            "final_id": get_latest_version_id(project_id, "final")
        })
    except Exception as e:
        logger.error(f"多代理流程错误: {str(e)}")
        logger.error(traceback.format_exc())
        # 更新项目状态为错误
        try:
            project = PaperProject.query.get(project_id)
            project.status = "error"
            db.session.commit()
            log_agent_activity(project_id, 'system', f'多代理流程出错: {str(e)}')
        except:
            pass
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-interactive-multi-agent', methods=['POST'])
def api_start_interactive_multi_agent_legacy(project_id):
    """[DEPRECATED] 请使用 /api/projects/<int:project_id>/start_interactive_multi_agent
    
    启动交互式多代理协作流程，在监督Agent的协调下完成研究、写作、审阅和修订
    
    这个API会启动一个交互式协作工作流，由监督代理协调整个过程，研究代理查找相关文献，
    写作代理根据研究成果撰写论文，审阅代理对初稿进行审阅并提供建议，监督代理评估审阅意见，
    决定是让写作代理接受修改建议还是让审阅代理提供更好的反馈。最终在审阅代理满意后完成论文。
    """
    # Redirect to the new route with underscore
    return api_start_interactive_multi_agent(project_id)

@app.route('/api/projects/<int:project_id>/start_interactive_multi_agent', methods=['POST'])
def api_start_interactive_multi_agent(project_id):
    """启动交互式多代理协作流程，在监督Agent的协调下完成研究、写作、审阅和修订
    
    这个API会启动一个交互式协作工作流，由监督代理协调整个过程，研究代理查找相关文献，
    写作代理根据研究成果撰写论文，审阅代理对初稿进行审阅并提供建议，监督代理评估审阅意见，
    决定是让写作代理接受修改建议还是让审阅代理提供更好的反馈。最终在审阅代理满意后完成论文。
    """
    try:
        # Get project
        project = PaperProject.query.get_or_404(project_id)
        
        # Initialize status tracking for this project
        agent_status[project_id] = {
            'mcp': {'status': 'Initializing', 'current_task': 'Starting up the multi-agent process'},
            'research': {'status': 'Idle', 'current_task': 'Waiting for instructions'},
            'writing': {'status': 'Idle', 'current_task': 'Waiting for research results'},
            'review': {'status': 'Idle', 'current_task': 'Waiting for draft'}
        }
        
        # Initialize interactions
        agent_interactions[project_id] = []
        
        # Initialize logs
        agent_logs[project_id] = []
        
        # Add initial log
        add_agent_log(project_id, 'system', 'Starting interactive multi-agent process')
        
        # Start the multi-agent process in a background thread to not block the response
        thread = threading.Thread(target=run_interactive_multi_agent_process, args=(project_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Interactive multi-agent process started'
        })
        
    except Exception as e:
        logger.error(f"Error starting interactive multi-agent process: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def run_interactive_multi_agent_process(project_id):
    """Run the interactive multi-agent process in background."""
    try:
        # Get project
        with app.app_context():
            project = PaperProject.query.get(project_id)
            if not project:
                add_agent_log(project_id, 'system', 'Error: Project not found', is_error=True)
                return
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Working', 'Coordinating the research process')
            add_agent_log(project_id, 'mcp', f'Starting multi-agent workflow for topic: {project.topic}')
            add_agent_interaction(project_id, 'MCP', 'Research', f'Requesting research on topic: {project.topic}')
            
            # PHASE 1: Research
            update_agent_status(project_id, 'research', 'Working', f'Researching topic: {project.topic}')
            add_agent_log(project_id, 'research', f'Starting research on topic: {project.topic}')
            
            try:
                research_agent = get_agent_for_project(project, 'research')
                research_result = research_agent.process(project.topic)
                
                # Save research results
                save_version(project_id, "research", research_result)
                
                update_agent_status(project_id, 'research', 'Complete', 'Research completed')
                add_agent_log(project_id, 'research', 'Research phase completed successfully')
                add_agent_interaction(project_id, 'Research', 'MCP', 'Research completed, sending results')
                
            except Exception as e:
                update_agent_status(project_id, 'research', 'Error', f'Error: {str(e)}')
                add_agent_log(project_id, 'research', f'Error during research: {str(e)}', is_error=True)
                add_agent_interaction(project_id, 'Research', 'MCP', 'Error during research phase')
                raise
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Working', 'Processing research results')
            add_agent_log(project_id, 'mcp', 'Research phase completed, initiating writing phase')
            add_agent_interaction(project_id, 'MCP', 'Writing', f'Requesting paper draft based on research')
            
            # PHASE 2: Writing
            update_agent_status(project_id, 'writing', 'Working', 'Writing paper draft based on research')
            add_agent_log(project_id, 'writing', 'Starting paper draft writing')
            
            try:
                writing_agent = get_agent_for_project(project, 'writing')
                paper_draft = writing_agent.process(project.topic, research_result)
                
                # Save draft
                save_version(project_id, "draft", paper_draft)
                
                update_agent_status(project_id, 'writing', 'Complete', 'Draft completed')
                add_agent_log(project_id, 'writing', 'Paper draft completed successfully')
                add_agent_interaction(project_id, 'Writing', 'MCP', 'Paper draft completed, sending draft')
                
            except Exception as e:
                update_agent_status(project_id, 'writing', 'Error', f'Error: {str(e)}')
                add_agent_log(project_id, 'writing', f'Error during writing: {str(e)}', is_error=True)
                add_agent_interaction(project_id, 'Writing', 'MCP', 'Error during writing phase')
                raise
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Working', 'Processing draft')
            add_agent_log(project_id, 'mcp', 'Writing phase completed, initiating review phase')
            add_agent_interaction(project_id, 'MCP', 'Review', f'Requesting review of paper draft')
            
            # PHASE 3: Review
            update_agent_status(project_id, 'review', 'Working', 'Reviewing paper draft')
            add_agent_log(project_id, 'review', 'Starting paper review')
            
            try:
                review_agent = get_agent_for_project(project, 'review')
                review_feedback = review_agent.process(project.topic, paper_draft)
                
                # Ensure feedback is a string with proper Markdown formatting
                if isinstance(review_feedback, list):
                    # If it's a list, join with newlines and ensure proper Markdown
                    feedback_str = ""
                    for item in review_feedback:
                        if item.startswith('## '):
                            # It's already a heading
                            feedback_str += f"{item}\n\n"
                        else:
                            # It's a bullet point
                            feedback_str += f"- {item}\n"
                    review_feedback = feedback_str
                elif not isinstance(review_feedback, str):
                    # Convert any other type to string and wrap in markdown
                    review_feedback = f"## Review Feedback\n\n{str(review_feedback)}"
                
                # Save review
                save_version(project_id, "review", review_feedback)
                
                update_agent_status(project_id, 'review', 'Complete', 'Review completed')
                add_agent_log(project_id, 'review', 'Paper review completed successfully')
                add_agent_interaction(project_id, 'Review', 'MCP', 'Review completed, sending feedback')
                
            except Exception as e:
                update_agent_status(project_id, 'review', 'Error', f'Error: {str(e)}')
                add_agent_log(project_id, 'review', f'Error during review: {str(e)}', is_error=True)
                add_agent_interaction(project_id, 'Review', 'MCP', 'Error during review phase')
                raise
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Working', 'Processing review feedback')
            add_agent_log(project_id, 'mcp', 'Review phase completed, initiating final revision')
            add_agent_interaction(project_id, 'MCP', 'Writing', f'Requesting final revision based on review feedback')
            
            # PHASE 4: Final Revision
            update_agent_status(project_id, 'writing', 'Working', 'Revising paper based on review')
            add_agent_log(project_id, 'writing', 'Starting final revision')
            
            try:
                # Get the writing agent again (or reuse if cached)
                writing_agent = get_agent_for_project(project, 'writing')
                final_paper = writing_agent.revise_draft(paper_draft, review_feedback)
                
                # Save final version
                save_version(project_id, "final", final_paper)
                
                update_agent_status(project_id, 'writing', 'Complete', 'Final revision completed')
                add_agent_log(project_id, 'writing', 'Final paper revision completed successfully')
                add_agent_interaction(project_id, 'Writing', 'MCP', 'Final revision completed, sending final paper')
                
            except Exception as e:
                update_agent_status(project_id, 'writing', 'Error', f'Error: {str(e)}')
                add_agent_log(project_id, 'writing', f'Error during final revision: {str(e)}', is_error=True)
                add_agent_interaction(project_id, 'Writing', 'MCP', 'Error during final revision phase')
                raise
            
            # Mark project as completed
            project.status = "completed"
            db.session.commit()
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Complete', 'All phases completed successfully')
            add_agent_log(project_id, 'mcp', 'Multi-agent workflow completed successfully')
            add_agent_log(project_id, 'system', 'Interactive multi-agent process completed')
            
    except Exception as e:
        logger.error(f"Error in interactive multi-agent process: {str(e)}")
        traceback.print_exc()
        
        with app.app_context():
            # Update project status to failed
            project = PaperProject.query.get(project_id)
            if project:
                project.status = "failed"
                db.session.commit()
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Error', f'Process failed: {str(e)}')
            add_agent_log(project_id, 'system', f'Process failed with error: {str(e)}', is_error=True)

def update_agent_status(project_id, agent_id, status, current_task=None):
    """Update the status of an agent in the interactive process."""
    if project_id not in agent_status:
        agent_status[project_id] = {}
    
    if agent_id not in agent_status[project_id]:
        agent_status[project_id][agent_id] = {}
    
    agent_status[project_id][agent_id]['status'] = status
    
    if current_task:
        agent_status[project_id][agent_id]['current_task'] = current_task

def add_agent_interaction(project_id, from_agent, to_agent, message):
    """Add an interaction between agents."""
    if project_id not in agent_interactions:
        agent_interactions[project_id] = []
    
    agent_interactions[project_id].append({
        'from': from_agent,
        'to': to_agent,
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def add_agent_log(project_id, agent, message, is_error=False):
    """Add a log entry for an agent."""
    if project_id not in agent_logs:
        agent_logs[project_id] = []
    
    log_type = 'error' if is_error else 'info'
    
    agent_logs[project_id].append({
        'agent': agent,
        'message': message,
        'type': log_type,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/projects/<int:project_id>/multi_agent_status', methods=['GET'])
def api_get_multi_agent_status(project_id):
    """Get the current status of all agents in the interactive process."""
    project = PaperProject.query.get_or_404(project_id)
    
    # Get agent status
    status = agent_status.get(project_id, {})
    
    # Get agent interactions
    interactions = agent_interactions.get(project_id, [])
    
    # Check if process is complete
    is_complete = all(agent.get('status') == 'Complete' for agent in status.values()) if status else False
    
    return jsonify({
        'agents': status,
        'interactions': interactions,
        'is_complete': is_complete
    })

@app.route('/api/projects/<int:project_id>/multi_agent_logs', methods=['GET'])
def api_get_multi_agent_logs(project_id):
    """Get the logs for the interactive multi-agent process."""
    project = PaperProject.query.get_or_404(project_id)
    
    # Get agent logs
    logs = agent_logs.get(project_id, [])
    
    return jsonify({
        'logs': logs
    })

def get_latest_version(project_id, content_type):
    """Get the latest version of a given content type for a project."""
    return PaperVersion.query.filter_by(
        project_id=project_id, 
        content_type=content_type
    ).order_by(PaperVersion.version_number.desc()).first()

def get_latest_version_id(project_id, content_type):
    """Get the ID of the latest version for a given project and content type."""
    try:
        latest_version = PaperVersion.query.filter_by(
            project_id=project_id, 
            content_type=content_type
        ).order_by(PaperVersion.version_number.desc()).first()
        
        if latest_version:
            return latest_version.id
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting latest version ID: {str(e)}")
        return None

def save_version(project_id, content_type, content):
    """Save a version of paper content."""
    # Get the project
    project = PaperProject.query.get(project_id)
    if not project:
        logger.error(f"Project {project_id} not found")
        return None
        
    # Get the latest version number
    latest_version = PaperVersion.query.filter_by(
        project_id=project_id, 
        content_type=content_type
    ).order_by(PaperVersion.version_number.desc()).first()
    
    version_number = 1
    if latest_version:
        version_number = latest_version.version_number + 1
        
    # Create a new version
    version = PaperVersion(
        project_id=project_id,
        content_type=content_type,
        content=content,
        version_number=version_number
    )
    
    db.session.add(version)
    db.session.commit()
    
    return version

@app.route('/api/projects/<int:project_id>/delete', methods=['POST'])
def api_delete_project(project_id):
    """Delete a project and all its associated data."""
    try:
        # Get the project
        project = PaperProject.query.get_or_404(project_id)
        
        logger.info(f"[Project {project_id}] Deleting project: {project.topic}")
        
        try:
            # Delete the project - cascade will automatically delete related records
            db.session.delete(project)
            db.session.commit()
            
            logger.info(f"[Project {project_id}] Project deleted successfully")
            return jsonify({
                'status': 'success',
                'message': 'Project deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"[Project {project_id}] Error deleting project: {str(e)}")
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Error deleting project: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in delete project endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error deleting project: {str(e)}'
        }), 500

@app.route('/api/projects/<int:project_id>/export', methods=['GET'])
def api_export_paper(project_id):
    """Export a paper in HTML or PDF format"""
    try:
        # Get the requested export format, default is HTML
        export_format = request.args.get('format', 'html').lower()
        
        # Check if PDF is requested but not supported
        PDF_SUPPORT = False
        try:
            from weasyprint import HTML
            from io import BytesIO
            PDF_SUPPORT = True
        except ImportError:
            PDF_SUPPORT = False
            
        if export_format == 'pdf' and not PDF_SUPPORT:
            logger.warning("PDF export was requested, but the system doesn't support PDF generation. Falling back to HTML format.")
            export_format = 'html'
        
        # Get the project
        project = PaperProject.query.get_or_404(project_id)
        
        # Get the latest version of the paper
        paper_version = PaperVersion.query.filter_by(
            project_id=project_id
        ).order_by(PaperVersion.version_number.desc()).first()
        
        if not paper_version:
            return jsonify({'status': 'error', 'error': 'No paper version found'}), 404
        
        # Convert Markdown to HTML
        import markdown2
        html_content = markdown2.markdown(paper_version.content)
        
        # Create a complete HTML document with styling
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{project.topic}</title>
            <style>
                body {{
                    font-family: 'Times New Roman', Times, serif;
                    line-height: 1.6;
                    margin: 3cm;
                    max-width: 800px;
                    margin-left: auto;
                    margin-right: auto;
                    color: #333;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #000;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{
                    font-size: 24pt;
                    text-align: center;
                    font-weight: bold;
                    margin-bottom: 1.5em;
                }}
                h2 {{
                    font-size: 18pt;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 0.2em;
                }}
                h3 {{ font-size: 16pt; }}
                h4 {{ font-size: 14pt; }}
                p {{
                    margin-bottom: 1em;
                    text-align: justify;
                }}
                .abstract {{
                    font-style: italic;
                    margin: 2em 0;
                    padding: 1em;
                    border: 1px solid #ddd;
                    background-color: #f9f9f9;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1em 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
                th {{
                    padding-top: 12px;
                    padding-bottom: 12px;
                    text-align: left;
                    background-color: #f2f2f2;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 1em auto;
                }}
                .citation {{
                    font-size: 10pt;
                }}
                .references {{
                    margin-top: 2em;
                    border-top: 1px solid #ddd;
                    padding-top: 1em;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Return HTML or PDF based on the requested format
        if export_format == 'html':
            # Return HTML
            from flask import Response
            return Response(
                styled_html,
                mimetype='text/html',
                headers={'Content-Disposition': f'attachment; filename={project.topic}.html'}
            )
        elif export_format == 'pdf' and PDF_SUPPORT:
            try:
                # Try to generate PDF
                pdf = HTML(string=styled_html).write_pdf()
                
                # Return PDF
                from flask import send_file
                return send_file(
                    BytesIO(pdf),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"{project.topic}.pdf"
                )
            except Exception as e:
                # If PDF generation fails, log the error and return HTML
                logger.error(f"PDF generation failed: {str(e)}")
                logger.info("Falling back to HTML format")
                
                return Response(
                    styled_html,
                    mimetype='text/html',
                    headers={'Content-Disposition': f'attachment; filename={project.topic}.html'}
                )
        else:
            # Unsupported format
            return jsonify({'status': 'error', 'error': 'Unsupported format'}), 400
    except Exception as e:
        logger.error(f"Error exporting paper: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/paper-types', methods=['GET'])
def api_get_paper_types():
    """获取所有论文类型"""
    try:
        from utils.paper_types import get_paper_types
        return jsonify(get_paper_types())
    except ImportError:
        # Fallback if module not found
        default_types = {
            "regular": {
                "name": "Regular Research Paper",
                "description": "A full-length research paper presenting original research."
            }
        }
        return jsonify(default_types)

@app.route('/api/languages', methods=['GET'])
def api_get_languages():
    """获取所有支持的语言"""
    try:
        from utils.paper_types import get_languages
        return jsonify(get_languages())
    except ImportError:
        # Fallback if module not found
        default_languages = {
            "en": {
                "name": "English",
                "description": "Standard academic English"
            }
        }
        return jsonify(default_languages)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)