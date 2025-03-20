"""
Academic Agent Suite - Main Application (Fixed Version)

This is the fixed version of the application with improved error handling,
better diagnostic capabilities, and more robust multi-agent coordination.
It provides a web interface for creating academic papers using AI agents.

Key improvements over the original app.py:
- Robust error handling in the multi-agent process to prevent crashes
- Diagnostic endpoints for troubleshooting
- Configurable UI features through environment variables
- Improved scholarly library integration with better timeout handling

Main components:
- Flask web application with routes for UI and API endpoints
- Database models for projects and paper versions
- Integration with research, writing, and review agents
- Multi-agent coordination for the complete academic paper generation process
"""

import os
import logging
import json
import traceback
import threading
import socket
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from agents.review_agent_fixed import ReviewAgent
from agents.supervisor_agent import SupervisorAgent
from dotenv import load_dotenv
import markdown2
from io import BytesIO

# Load environment variables
load_dotenv()

# Application configuration
APP_CONFIG = {
    'ENABLE_MULTI_AGENT': os.environ.get('ENABLE_MULTI_AGENT', 'true').lower() == 'true',
    'DEFAULT_MODEL_TYPE': os.environ.get('DEFAULT_MODEL_TYPE', 'siliconflow'),
    'DEFAULT_RESEARCH_SOURCE': os.environ.get('DEFAULT_RESEARCH_SOURCE', 'arxiv')
}

# Configure scholarly to not use proxies (must be done before any other imports)
try:
    import socket
    # Set longer timeout for scholarly connections
    default_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10.0)  # 10 seconds timeout
    
    from scholarly import scholarly
    scholarly.use_proxy(None, None)
    logging.info("Configured scholarly to not use proxies")
    
    # Restore default timeout
    socket.setdefaulttimeout(default_timeout)
except Exception as e:
    logging.warning(f"Failed to configure scholarly proxy settings: {str(e)}")
    logging.warning("Continuing without scholarly configuration - research using Google Scholar may be limited")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "default_secret_key")

# Make configuration available to templates
@app.context_processor
def inject_app_config():
    return {'app_config': APP_CONFIG}

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI", 'sqlite:///instance/paper_projects.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    
    This filter ensures that academic papers are properly formatted with:
    1. Proper Markdown rendering if content is in markdown format
    2. LaTeX equations properly formatted for MathJax
    3. Code blocks properly syntax-highlighted
    4. Tables correctly formatted
    
    Args:
        content: The academic content (paper draft, review, etc.)
        
    Returns:
        Processed content with HTML markup for proper rendering
    """
    try:
        import re
        
        # Skip processing if content is already HTML
        if content.strip().startswith('<') and '<html' in content.lower():
            return content
        
        # Add classes to LaTeX equations for better styling
        # Inline equations: $...$
        content = re.sub(r'(\$[^\$]+\$)', r'<span class="math inline">\1</span>', content)
        
        # Display equations: $$...$$
        content = re.sub(r'(\$\$[^\$]+\$\$)', r'<div class="math display">\1</div>', content)
        
        # Add classes to code blocks for better styling
        if '```' in content:
            # Process code blocks with language specification: ```python
            content = re.sub(
                r'```(\w*)\n(.*?)\n```',
                r'<pre class="code-block language-\1"><code>\2</code></pre>',
                content, 
                flags=re.DOTALL
            )
        
        # Add citation formatting
        content = re.sub(r'\[@([^\]]+)\]', r'<cite class="citation">[\1]</cite>', content)
        
        # If markdown package is available, use it for better formatting
        try:
            import markdown
            html_content = markdown.markdown(
                content,
                extensions=[
                    'markdown.extensions.extra',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.tables'
                ]
            )
            return html_content
        except ImportError:
            # Fallback: just return the content with basic enhancements
            return content
            
    except Exception as e:
        logger.error(f"Error processing academic content: {str(e)}")
        # Return original content if processing fails
        return content

# Initialize SQLAlchemy with app
db = SQLAlchemy(app)

# Initialize agents with the default model 
model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")

# Cache for agent instances
_agent_cache = {}

# 日志缓存，记录每个项目的代理工作日志
project_logs = {}

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
    """Create and return an agent instance configured for the specific project.
    
    This is a factory function that creates agent instances based on the project's
    configuration settings, such as the model type and custom model parameters.
    
    Args:
        project: The PaperProject instance containing project configuration
        agent_type: String indicating agent type to create ('research', 'writing', 'review')
    
    Returns:
        An initialized agent instance of the requested type, configured for the project
        
    Raises:
        ValueError: If the agent_type is unknown
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

def get_review_agent(model_type=None, custom_model_name=None, custom_model_endpoint=None, 
                   custom_model_api_key=None, custom_model_temperature=None):
    """Create and return a review agent."""
    try:
        # First try to use the fixed review agent
        from agents.review_agent_fixed import ReviewAgent
        logger.info("Using fixed review agent")
        
        # If model_type is not specified, use default from environment
        if model_type is None:
            model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
            
        # Configure custom model if needed
        custom_model_config = None
        if model_type == 'custom' and custom_model_endpoint and custom_model_name:
            custom_model_config = {
                'endpoint': custom_model_endpoint,
                'api_key': custom_model_api_key,
                'model_name': custom_model_name,
                'temperature': custom_model_temperature or 0.7
            }
            
        return ReviewAgent(model_type=model_type, custom_model_config=custom_model_config)
    except ImportError:
        # Fall back to original review agent if fixed version is not available
        logger.warning("Fixed review agent not found, falling back to original")
        from agents.review_agent import ReviewAgent
        
        # If model_type is not specified, use default from environment
        if model_type is None:
            model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
            
        # Configure custom model if needed
        custom_model_config = None
        if model_type == 'custom' and custom_model_endpoint and custom_model_name:
            custom_model_config = {
                'endpoint': custom_model_endpoint,
                'api_key': custom_model_api_key,
                'model_name': custom_model_name,
                'temperature': custom_model_temperature or 0.7
            }
            
        return ReviewAgent(model_type=model_type, custom_model_config=custom_model_config)

def get_supervisor_agent():
    """Create and return a supervisor agent."""
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    return SupervisorAgent(model_type=model_type)

# Interactive Multi-Agent Visualization Data Storage
agent_status = {}  # Store agent status for each project
agent_interactions = {}  # Store agent interactions for each project
agent_logs = {}  # Store detailed agent logs for each project

@app.route('/api/projects/<int:project_id>/start_interactive_multi_agent', methods=['POST'])
def api_start_interactive_multi_agent(project_id):
    """Start the interactive multi-agent workflow with visualization."""
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
    """Run the interactive multi-agent process in background.
    
    This function orchestrates the collaboration between multiple agents
    to complete the entire research, writing, and review process. It runs
    as a background thread and updates the project status and logs throughout.
    
    The process consists of four main phases:
    1. Research: Research agent gathers information on the topic
    2. Writing: Writing agent creates a draft based on research
    3. Review: Review agent evaluates the draft
    4. Final Revision: Writing agent revises the draft based on review feedback
    
    Each phase includes robust error handling to prevent crashes and
    record detailed logs about progress or failures.
    
    Args:
        project_id: ID of the project to process
        
    Returns:
        None - The function updates the database and logs instead of returning values
    """
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
                # Don't immediately raise - set status and continue with error handling
                with app.app_context():
                    project.status = "failed"
                    db.session.commit()
                    
                update_agent_status(project_id, 'mcp', 'Error', f'Process failed at research phase: {str(e)}')
                add_agent_log(project_id, 'system', f'Process failed with error during research: {str(e)}', is_error=True)
                return
            
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
                # Don't immediately raise - set status and continue with error handling
                with app.app_context():
                    project.status = "failed"
                    db.session.commit()
                    
                update_agent_status(project_id, 'mcp', 'Error', f'Process failed at writing phase: {str(e)}')
                add_agent_log(project_id, 'system', f'Process failed with error during writing: {str(e)}', is_error=True)
                return
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Working', 'Processing draft')
            add_agent_log(project_id, 'mcp', 'Writing phase completed, initiating review phase')
            add_agent_interaction(project_id, 'MCP', 'Review', f'Requesting review of paper draft')
            
            # PHASE 3: Review
            update_agent_status(project_id, 'review', 'Working', 'Reviewing paper draft')
            add_agent_log(project_id, 'review', 'Starting paper review')
            
            try:
                review_agent = get_review_agent(project.model_type, project.custom_model_name, project.custom_model_endpoint, 
                                               project.custom_model_api_key, project.custom_model_temperature)
                review_feedback = review_agent.process(project.topic, paper_draft)
                
                # Convert review feedback to string if it's not already
                if not isinstance(review_feedback, str):
                    review_feedback_str = json.dumps(review_feedback, ensure_ascii=False)
                else:
                    review_feedback_str = review_feedback
                
                # Save review
                save_version(project_id, "review", review_feedback_str)
                
                update_agent_status(project_id, 'review', 'Complete', 'Review completed')
                add_agent_log(project_id, 'review', 'Paper review completed successfully')
                add_agent_interaction(project_id, 'Review', 'MCP', 'Review completed, sending feedback')
                
            except Exception as e:
                update_agent_status(project_id, 'review', 'Error', f'Error: {str(e)}')
                add_agent_log(project_id, 'review', f'Error during review: {str(e)}', is_error=True)
                add_agent_interaction(project_id, 'Review', 'MCP', 'Error during review phase')
                # Don't immediately raise - set status and continue with error handling
                with app.app_context():
                    project.status = "failed"
                    db.session.commit()
                    
                update_agent_status(project_id, 'mcp', 'Error', f'Process failed at review phase: {str(e)}')
                add_agent_log(project_id, 'system', f'Process failed with error during review: {str(e)}', is_error=True)
                return
            
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
                # Don't immediately raise - set status and continue with error handling
                with app.app_context():
                    project.status = "failed"
                    db.session.commit()
                    
                update_agent_status(project_id, 'mcp', 'Error', f'Process failed at final revision phase: {str(e)}')
                add_agent_log(project_id, 'system', f'Process failed with error during final revision: {str(e)}', is_error=True)
                return
            
            # Mark project as completed
            with app.app_context():
                project.status = "completed"
                db.session.commit()
            
            # Update MCP status
            update_agent_status(project_id, 'mcp', 'Complete', 'All phases completed successfully')
            add_agent_log(project_id, 'mcp', 'Multi-agent workflow completed successfully')
            add_agent_log(project_id, 'system', 'Interactive multi-agent process completed')
            
    except Exception as e:
        logger.error(f"Error in interactive multi-agent process: {str(e)}")
        traceback.print_exc()
        
        try:
            with app.app_context():
                # Update project status to failed
                project = PaperProject.query.get(project_id)
                if project:
                    project.status = "failed"
                    db.session.commit()
                
                # Update MCP status
                update_agent_status(project_id, 'mcp', 'Error', f'Process failed: {str(e)}')
                add_agent_log(project_id, 'system', f'Process failed with error: {str(e)}', is_error=True)
        except Exception as inner_e:
            logger.error(f"Error updating status after failure: {str(inner_e)}")

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

def save_version(project_id, content_type, content):
    """Save a version of paper content."""
    with app.app_context():
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

def get_latest_version_id(project_id, content_type):
    """Get the ID of the latest version for a given project and content type."""
    try:
        with app.app_context():
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

@app.route('/api/debug/multi-agent-test/<int:project_id>', methods=['GET'])
def debug_multi_agent(project_id):
    """Debug route to test multi-agent initialization and diagnose issues.
    
    This diagnostic endpoint tests various components of the multi-agent process
    without actually running the complete process. It helps identify where issues
    might be occurring when the multi-agent process fails.
    
    Tests performed:
    1. Project retrieval and property validation
    2. Agent initialization for all agent types
    3. Basic agent functionality testing
    4. Database operations (save_version and get_latest_version_id)
    
    Args:
        project_id: ID of the project to test
        
    Returns:
        JSON object with detailed diagnostic information about each test
    """
    try:
        # 1. Get project and check if it exists
        project = PaperProject.query.get_or_404(project_id)
        
        # 2. Record detailed diagnostics
        diagnostics = {
            'project': {},
            'agent_initialization': {},
            'agent_process_test': {},
            'database_operations': {}
        }
        
        # 3. Check project properties    
        diagnostics['project'] = {
            'id': project.id,
            'topic': project.topic,
            'model_type': project.model_type,
            'research_source': project.research_source,
            'status': project.status,
        }
        
        # 4. Test agent initialization
        agent_types = ['research', 'writing', 'review']
        for agent_type in agent_types:
            try:
                agent = get_agent_for_project(project, agent_type)
                diagnostics['agent_initialization'][agent_type] = {
                    'success': True,
                    'class': agent.__class__.__name__
                }
            except Exception as e:
                diagnostics['agent_initialization'][agent_type] = {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        # 5. Test minimal agent functionality (without running full process)
        # This will help identify if the agents can be initialized and their basic methods work
        for agent_type in agent_types:
            if diagnostics['agent_initialization'][agent_type]['success']:
                try:
                    agent = get_agent_for_project(project, agent_type)
                    # Just test getting progress - this doesn't make API calls but tests basic agent functionality
                    progress = agent.get_progress()
                    diagnostics['agent_process_test'][agent_type] = {
                        'success': True,
                        'progress': progress
                    }
                except Exception as e:
                    diagnostics['agent_process_test'][agent_type] = {
                        'success': False,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
        
        # 6. Test database operations
        try:
            # Test version saving with a minimal test content
            test_content = json.dumps({
                'test': True,
                'timestamp': datetime.now().isoformat()
            })
            test_version = save_version(project_id, "test", test_content)
            
            # Test retrieving the latest version ID
            test_version_id = get_latest_version_id(project_id, "test")
            
            diagnostics['database_operations'] = {
                'save_version': {
                    'success': True,
                    'version_id': test_version.id if test_version else None
                },
                'get_latest_version_id': {
                    'success': test_version_id is not None,
                    'version_id': test_version_id
                }
            }
            
            # Clean up test version
            if test_version:
                with app.app_context():
                    db.session.delete(test_version)
                    db.session.commit()
                    
        except Exception as e:
            diagnostics['database_operations'] = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        
        # 7. Overall diagnosis
        all_tests_passed = all([
            all(test['success'] for test in diagnostics['agent_initialization'].values()),
            all(test['success'] for test in diagnostics['agent_process_test'].values()),
            diagnostics['database_operations'].get('save_version', {}).get('success', False),
            diagnostics['database_operations'].get('get_latest_version_id', {}).get('success', False)
        ])
        
        diagnostics['overall'] = {
            'success': all_tests_passed,
            'message': 'All diagnostic tests passed successfully' if all_tests_passed else 'Some diagnostic tests failed'
        }
        
        return jsonify({
            'status': 'success',
            'diagnostics': diagnostics,
            'recommendation': 'All systems operational, multi-agent process should work correctly' if all_tests_passed 
                             else 'Issues detected, check the diagnostics for details on which components failed'
        })
            
    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/test-research/<int:project_id>', methods=['GET'])
def debug_test_research(project_id):
    """Debug route to test only the research agent without starting the full multi-agent process.
    
    This endpoint initializes just the research agent and tests its basic functionality
    without making external API calls. It uses a test subclass that overrides the process
    method to avoid actual research API requests.
    
    This is useful for diagnosing issues specific to the research agent initialization
    and minimal functionality.
    
    Args:
        project_id: ID of the project to test
        
    Returns:
        JSON object with diagnostic information about the research agent
    """
    try:
        # Get project
        project = PaperProject.query.get_or_404(project_id)
        
        # Create a test topic if none exists
        test_topic = project.topic if project.topic else "Machine Learning in Healthcare"
        
        # Initialize research agent
        try:
            # Initialize the research agent
            research_agent = get_agent_for_project(project, 'research')
            agent_initialized = True
            agent_info = {
                'class': research_agent.__class__.__name__,
                'progress': research_agent.get_progress(),
                'research_sources': getattr(research_agent, 'research_sources', ['unknown'])
            }
        except Exception as e:
            agent_initialized = False
            agent_info = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        
        # If agent initialized, try a minimal test (stop after progress=10 to avoid full API calls)
        research_data = None
        process_success = False
        process_error = None
        
        if agent_initialized:
            # Create a subclass that overrides process to stop early
            class TestResearchAgent(research_agent.__class__):
                def process(self, topic):
                    """Override to only do minimal initialization without API calls."""
                    logger.info(f"Test starting research process on topic: {topic}")
                    self.progress = 10
                    # Return a minimal valid result
                    return json.dumps({
                        'papers': [],
                        'summary': f"Test summary for {topic}",
                        'analysis': {
                            'key_findings': ['Test finding'],
                            'methodologies': ['Test methodology'],
                            'research_gaps': ['Test gap']
                        },
                        'source': 'test',
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Apply the test subclass methods to our agent
            research_agent.__class__ = TestResearchAgent
            
            try:
                # Run the minimal process test
                research_data = research_agent.process(test_topic)
                process_success = True
            except Exception as e:
                process_success = False
                process_error = {
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        # Return diagnostics
        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'test_topic': test_topic,
            'agent_initialized': agent_initialized,
            'agent_info': agent_info,
            'process_success': process_success,
            'process_error': process_error,
            'research_data_sample': research_data[:200] + '...' if research_data and len(research_data) > 200 else research_data
        })
        
    except Exception as e:
        logger.error(f"Research agent test error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/review/<int:project_id>', methods=['GET'])
def debug_review_agent(project_id):
    """Debug endpoint to test the review agent without actually saving anything."""
    try:
        # Get project
        project = PaperProject.query.get_or_404(project_id)
        
        # Get the latest draft
        latest_draft = get_latest_version(project_id, 'draft')
        if not latest_draft:
            return jsonify({'error': 'No draft found for review'}), 400
        
        # Create diagnostic information
        diagnostics = {
            'project': {
                'id': project.id,
                'topic': project.topic,
                'model_type': project.model_type
            },
            'draft': {
                'id': latest_draft.id,
                'length': len(latest_draft.content)
            },
            'agent_test': {}
        }
        
        # Test the review agent
        try:
            # First test connection
            from agents.review_agent_fixed import ReviewAgent
            review_agent = ReviewAgent(model_type=project.model_type)
            
            # Test connection
            connection_success, connection_message = review_agent.test_connection()
            diagnostics['agent_test']['connection'] = {
                'success': connection_success,
                'message': connection_message
            }
            
            if connection_success:
                # Try processing just a small part of the draft to test
                test_content = latest_draft.content[:1000] + "...[content truncated for test]"
                test_feedback = review_agent.process(project.topic, test_content)
                
                diagnostics['agent_test']['process'] = {
                    'success': True,
                    'feedback': test_feedback
                }
            
        except Exception as e:
            logger.error(f"Error testing review agent: {str(e)}")
            logger.error(traceback.format_exc())
            diagnostics['agent_test']['error'] = {
                'message': str(e),
                'traceback': traceback.format_exc()
            }
        
        return jsonify(diagnostics)
        
    except Exception as e:
        logger.error(f"Error in debug review endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/projects/<int:project_id>/start-writing', methods=['POST'])
def api_start_writing(project_id):
    """Start the writing process for a project."""
    try:
        # Get project
        project = PaperProject.query.get_or_404(project_id)
        
        # Update project status
        project.status = 'writing'
        db.session.commit()
        
        # Record start message
        message = AgentMessage(
            project_id=project_id,
            sender='system',
            content=f"Starting writing process for project: {project.topic}",
            message_type='status'
        )
        db.session.add(message)
        db.session.commit()
        
        # Start the writing process in a background thread
        thread = threading.Thread(target=run_writing_process, args=(project_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Writing process started'
        })
        
    except Exception as e:
        logger.error(f"Error starting writing: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def run_writing_process(project_id):
    """Run the writing process for a project."""
    try:
        with app.app_context():
            # Get project
            project = PaperProject.query.get(project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return
            
            logger.info(f"[Project {project_id}] writing: Starting writing process")
            
            # Get research results
            research_version = get_latest_version(project_id, 'research')
            if not research_version:
                logger.error(f"[Project {project_id}] writing: No research results found")
                
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='writing_agent',
                    content=f"Error: No research results found. Complete the research phase before writing.",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status back to research_complete if it has research
                if project.research_completed:
                    project.status = 'research_complete'
                else:
                    project.status = 'created'
                
                db.session.commit()
                return
            
            try:
                # Initialize writing agent
                writing_agent = get_writing_agent()
                
                # Get research content
                research_content = research_version.content
                
                # Start writing process
                paper_content = writing_agent.process(project.topic, research_content)
                
                if paper_content:
                    # Create new version for the paper
                    version = PaperVersion(
                        project_id=project_id,
                        content=paper_content,
                        version_number=1,
                        created_by='writing_agent',
                        version_type='draft',
                        content_type='draft'
                    )
                    db.session.add(version)
                    
                    # Update project status
                    project.status = 'writing_complete'
                    project.writing_completed = True
                    
                    # Record success message
                    writing_complete_msg = AgentMessage(
                        project_id=project_id,
                        sender='writing_agent',
                        content=f"Successfully wrote paper draft on topic: {project.topic}",
                        message_type='result'
                    )
                    db.session.add(writing_complete_msg)
                    
                    logger.info(f"[Project {project_id}] writing: Writing completed successfully")
                else:
                    # Record error
                    error_message = AgentMessage(
                        project_id=project_id,
                        sender='writing_agent',
                        content=f"Error: Failed to generate paper draft. The writing agent returned empty content.",
                        message_type='error'
                    )
                    db.session.add(error_message)
                    
                    # Update project status back to research_complete
                    project.status = 'research_complete'
                    logger.error(f"[Project {project_id}] writing: Failed to generate paper draft (empty content)")
                
                db.session.commit()
                
            except Exception as e:
                logger.error(f"[Project {project_id}] writing: Error in writing process: {str(e)}")
                traceback.print_exc()
                
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='writing_agent',
                    content=f"Error in writing process: {str(e)}",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status back to research_complete
                project.status = 'research_complete'
                db.session.commit()
                
    except Exception as e:
        logger.error(f"[Project {project_id}] writing: Unhandled error in writing process: {str(e)}")
        traceback.print_exc()
        
        try:
            with app.app_context():
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='system',
                    content=f"Unhandled error in writing process: {str(e)}",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status
                project = PaperProject.query.get(project_id)
                if project:
                    project.status = 'research_complete'
                    db.session.commit()
        except Exception as inner_e:
            logger.error(f"[Project {project_id}] writing: Error recording failure: {str(inner_e)}")
            traceback.print_exc()

@app.route('/api/projects/<int:project_id>/delete', methods=['POST'])
def api_delete_project(project_id):
    """Delete a project and all its associated data."""
    try:
        # Get the project
        project = PaperProject.query.get_or_404(project_id)
        
        logger.info(f"[Project {project_id}] Deleting project: {project.topic}")
        
        try:
            # Delete all messages associated with the project
            messages = AgentMessage.query.filter_by(project_id=project_id).all()
            for message in messages:
                db.session.delete(message)
                
            # Delete all versions associated with the project
            versions = PaperVersion.query.filter_by(project_id=project_id).all()
            for version in versions:
                db.session.delete(version)
            
            # Delete the project itself
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

@app.route('/api/projects/<int:project_id>/start-review', methods=['POST'])
def api_start_review(project_id):
    """Start the review process for a project."""
    try:
        # Get project
        project = PaperProject.query.get_or_404(project_id)
        
        # Update project status
        project.status = 'reviewing'
        db.session.commit()
        
        # Create a start message
        message = AgentMessage(
            project_id=project_id,
            sender='system',
            content=f"Starting review process for project: {project.topic}",
            message_type='status'
        )
        db.session.add(message)
        db.session.commit()
        
        # Start the review process in a background thread
        thread = threading.Thread(target=run_review_process, args=(project_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Review process started'
        })
        
    except Exception as e:
        logger.error(f"Error starting review: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def run_review_process(project_id):
    """Run the review process for a project."""
    try:
        with app.app_context():
            # Get project
            project = PaperProject.query.get(project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return
            
            logger.info(f"[Project {project_id}] review: Starting review process")
            
            # Get latest draft
            latest_draft = get_latest_version(project_id, 'draft')
            if not latest_draft:
                logger.error(f"[Project {project_id}] review: No draft found")
                
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='review_agent',
                    content=f"Error: No draft found. Complete the writing phase before reviewing.",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status back to writing_complete if it has a draft
                if project.writing_completed:
                    project.status = 'writing_complete'
                else:
                    project.status = 'research_complete'
                
                db.session.commit()
                return
            
            try:
                # Initialize review agent
                review_agent = get_review_agent(
                    project.model_type, 
                    project.custom_model_name, 
                    project.custom_model_endpoint, 
                    project.custom_model_api_key, 
                    project.custom_model_temperature
                )
                
                # First test connection to identify any API issues early
                connection_test = review_agent.test_connection()
                if isinstance(connection_test, dict) and connection_test.get('status') == 'error':
                    logger.error(f"[Project {project_id}] review: API connection test failed: {connection_test.get('message')}")
                    
                    # Record error
                    error_message = AgentMessage(
                        project_id=project_id,
                        sender='review_agent',
                        content=f"Error: Failed to connect to review API. {connection_test.get('message')}",
                        message_type='error'
                    )
                    db.session.add(error_message)
                    
                    # Update project status
                    project.status = 'writing_complete'
                    db.session.commit()
                    return
                
                # Start review process
                feedback = review_agent.process(project.topic, latest_draft.content)
                
                # Handle different return types
                if isinstance(feedback, list):
                    feedback_str = '\n'.join(feedback)
                elif not isinstance(feedback, str):
                    feedback_str = str(feedback)
                else:
                    feedback_str = feedback
                
                if feedback_str:
                    # Create new version for review feedback
                    version = PaperVersion(
                        project_id=project_id,
                        content=feedback_str,
                        version_number=1,
                        created_by='review_agent',
                        version_type='review',
                        content_type='review'
                    )
                    db.session.add(version)
                    
                    # Update project status
                    project.status = 'review_complete'
                    
                    # Record success message
                    review_complete_msg = AgentMessage(
                        project_id=project_id,
                        sender='review_agent',
                        content=f"Successfully reviewed paper on topic: {project.topic}",
                        message_type='result'
                    )
                    db.session.add(review_complete_msg)
                    
                    logger.info(f"[Project {project_id}] review: Review completed successfully")
                else:
                    # Record error
                    error_message = AgentMessage(
                        project_id=project_id,
                        sender='review_agent',
                        content=f"Error: Failed to generate review feedback. The review agent returned empty content.",
                        message_type='error'
                    )
                    db.session.add(error_message)
                    
                    # Update project status back to writing_complete
                    project.status = 'writing_complete'
                    logger.error(f"[Project {project_id}] review: Failed to generate review (empty content)")
                
                db.session.commit()
                
            except Exception as e:
                logger.error(f"[Project {project_id}] review: Error in review process: {str(e)}")
                traceback.print_exc()
                
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='review_agent',
                    content=f"Error in review process: {str(e)}",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status back to writing_complete
                project.status = 'writing_complete'
                db.session.commit()
                
    except Exception as e:
        logger.error(f"[Project {project_id}] review: Unhandled error in review process: {str(e)}")
        traceback.print_exc()
        
        try:
            with app.app_context():
                # Record error
                error_message = AgentMessage(
                    project_id=project_id,
                    sender='system',
                    content=f"Unhandled error in review process: {str(e)}",
                    message_type='error'
                )
                db.session.add(error_message)
                
                # Update project status
                project = PaperProject.query.get(project_id)
                if project:
                    project.status = 'writing_complete'
                    db.session.commit()
        except Exception as inner_e:
            logger.error(f"[Project {project_id}] review: Error recording failure: {str(inner_e)}")
            traceback.print_exc()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000) 