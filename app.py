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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "default_secret_key")

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI", 'sqlite:///instance/paper_projects.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    """Create a new paper project."""
    try:
        data = request.json
        topic = data.get('title')
        model_type = data.get('model_type', 'siliconflow')
        research_source = data.get('research_source', 'none')
        custom_model = data.get('custom_model', None)
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        with app.app_context():
            # Create a new project
            project = PaperProject(
                topic=topic,
                model_type=model_type,
                research_source=research_source
            )
            
            # 如果有自定义模型配置，保存到项目中
            if custom_model and model_type == 'custom':
                project.custom_model_endpoint = custom_model.get('endpoint')
                project.custom_model_api_key = custom_model.get('api_key')
                project.custom_model_name = custom_model.get('model_name')
                project.custom_model_temperature = float(custom_model.get('temperature', 0.7))
                project.custom_model_max_tokens = int(custom_model.get('max_tokens', 2000))
            
            db.session.add(project)
            db.session.commit()
            
            project_id = project.id
            
            # 记录活动
            log_agent_activity(project_id, 'system', f'Project created with topic: {topic}')
            
            # Redirect to project detail page
            return jsonify({
                'status': 'success',
                'id': project_id,
                'redirect_url': f'/projects/{project_id}'
            })
            
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    """Project detail page."""
    try:
        project = PaperProject.query.get(project_id)
        if not project:
            return render_template('error.html', message=f"Project with ID {project_id} not found")
        
        # Get all versions for this project
        versions = PaperVersion.query.filter_by(project_id=project_id).order_by(PaperVersion.version_number.desc()).all()
        
        # Determine if we have research results, draft, and review
        research = next((v for v in versions if v.content_type == 'research'), None)
        draft = next((v for v in versions if v.content_type == 'draft'), None)
        review = next((v for v in versions if v.content_type == 'review'), None)
        final = next((v for v in versions if v.content_type == 'final'), None)
        
        return render_template(
            'project_detail.html', 
            project=project, 
            research=research,
            draft=draft,
            review=review,
            final=final
        )
    except Exception as e:
        logger.error(f"Error showing project detail: {str(e)}")
        return render_template('error.html', message=f"Error: {str(e)}")

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get all projects."""
    try:
        projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
        result = []
        for project in projects:
            result.append({
                'id': project.id,
                'topic': project.topic,
                'status': project.status,
                'model_type': project.model_type,
                'research_source': project.research_source,
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
        
        return jsonify({
            'id': project.id,
            'topic': project.topic,
            'status': project.status,
            'model_type': project.model_type,
            'research_source': project.research_source,
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
            
            # 执行研究
            log_agent_activity(project_id, 'research', f'Researching topic: {project.topic}')
            result = research_agent.process(project.topic)
            
            # 记录活动
            log_agent_activity(project_id, 'research', 'Research completed successfully')
            
            # 将研究结果存储为一个版本
            version = PaperVersion(
                project_id=project_id,
                version_number=1,
                content_type='research',
                content=result
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
                "message": "Research started successfully"
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
    """Start the writing phase for a project."""
    try:
        project = PaperProject.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found"}), 404
        
        # 检查是否已完成研究阶段
        research_version = PaperVersion.query.filter_by(
            project_id=project_id, 
            content_type='research'
        ).first()
        
        if not research_version:
            return jsonify({
                "error": "Research phase has not been completed for this project"
            }), 400
        
        # 更新项目状态
        project.status = "writing"
        db.session.commit()
        
        # 记录活动
        log_agent_activity(project_id, 'system', f'Starting writing phase for topic: {project.topic}')
        
        # 异步执行写作任务
        # 在实际应用中应该使用Celery或其他异步任务队列
        # 这里为了简化，直接在请求中执行
        try:
            # 获取写作代理
            writing_agent = get_agent_for_project(project, 'writing')
            
            # 记录活动
            log_agent_activity(project_id, 'writing', 'Initializing writing agent')
            
            # 执行写作
            log_agent_activity(project_id, 'writing', f'Writing paper on topic: {project.topic}')
            result = writing_agent.process(project.topic, research_version.content)
            
            # 记录活动
            log_agent_activity(project_id, 'writing', 'Writing completed successfully')
            
            # 将写作结果存储为一个版本
            version = PaperVersion(
                project_id=project_id,
                version_number=1,
                content_type='draft',
                content=result
            )
            db.session.add(version)
            
            # 更新项目状态
            project.status = "writing_complete"
            db.session.commit()
            
            # 添加一条成功消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='writing',
                message_type='info',
                message='Writing completed successfully'
            )
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": "Writing started successfully"
            })
            
        except Exception as e:
            logger.error(f"Error during writing: {str(e)}")
            
            # 添加一条错误消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='writing',
                message_type='error',
                message=f'Error during writing: {str(e)}'
            )
            db.session.add(message)
            
            # 更新项目状态
            project.status = "writing_failed"
            db.session.commit()
            
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting writing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-review', methods=['POST'])
def api_start_review(project_id):
    """Start the review phase for a project."""
    try:
        project = PaperProject.query.get(project_id)
        if not project:
            return jsonify({"error": f"Project with ID {project_id} not found"}), 404
        
        # 检查是否已完成写作阶段
        draft_version = PaperVersion.query.filter_by(
            project_id=project_id, 
            content_type='draft'
        ).first()
        
        if not draft_version:
            return jsonify({
                "error": "Writing phase has not been completed for this project"
            }), 400
        
        # 更新项目状态
        project.status = "reviewing"
        db.session.commit()
        
        # 记录活动
        log_agent_activity(project_id, 'system', f'Starting review phase for project: {project.topic}')
        
        # 异步执行审阅任务
        # 在实际应用中应该使用Celery或其他异步任务队列
        # 这里为了简化，直接在请求中执行
        try:
            # 获取审阅代理
            review_agent = get_agent_for_project(project, 'review')
            
            # 记录活动
            log_agent_activity(project_id, 'review', 'Initializing review agent')
            
            # 执行审阅
            log_agent_activity(project_id, 'review', f'Reviewing paper on topic: {project.topic}')
            result = review_agent.process(project.topic, draft_version.content)
            
            # 记录活动
            log_agent_activity(project_id, 'review', 'Review completed successfully')
            
            # 将审阅结果存储为一个版本
            version = PaperVersion(
                project_id=project_id,
                version_number=1,
                content_type='review',
                content=result
            )
            db.session.add(version)
            
            # 更新项目状态
            project.status = "review_complete"
            db.session.commit()
            
            # 添加一条成功消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='review',
                message_type='info',
                message='Review completed successfully'
            )
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "message": "Review started successfully"
            })
            
        except Exception as e:
            logger.error(f"Error during review: {str(e)}")
            
            # 添加一条错误消息
            message = AgentMessage(
                project_id=project_id,
                agent_type='review',
                message_type='error',
                message=f'Error during review: {str(e)}'
            )
            db.session.add(message)
            
            # 更新项目状态
            project.status = "review_failed"
            db.session.commit()
            
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting review: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
def api_start_interactive_multi_agent(project_id):
    """启动交互式多代理协作流程，在监督Agent的协调下完成研究、写作、审阅和修订
    
    这个API会启动一个交互式协作工作流，由监督代理协调整个过程，研究代理查找相关文献，
    写作代理根据研究成果撰写论文，审阅代理对初稿进行审阅并提供建议，监督代理评估审阅意见，
    决定是让写作代理接受修改建议还是让审阅代理提供更好的反馈。最终在审阅代理满意后完成论文。
    """
    try:
        # 获取项目
        project = PaperProject.query.get_or_404(project_id)
        
        # 阻止重复处理
        if project.status == "completed":
            return jsonify({"error": "项目已完成"}), 400
        
        # 更新项目状态为处理中
        project.status = "interactive_processing"
        db.session.commit()
        
        # 记录开始交互式多代理处理
        log_agent_activity(project_id, 'system', f'开始增强版交互式多代理协作流程：监督 → 研究 → 写作 → 审阅 → 交流 → 迭代修订')
        
        # 初始化代理实例
        supervisor_agent = get_agent_for_project(project, 'supervisor')
        research_agent = get_agent_for_project(project, 'research')
        writing_agent = get_agent_for_project(project, 'writing')
        review_agent = get_agent_for_project(project, 'review')
        communication_agent = CommunicationAgent(model_type=project.model_type)
        
        # 创建代理ID和映射，用于通信
        agent_ids = {
            'supervisor': 'sup_1',
            'research': 'res_1',
            'writing': 'wri_1',
            'review': 'rev_1',
            'communication': 'com_1'
        }
        
        agents = {
            agent_ids['supervisor']: supervisor_agent,
            agent_ids['research']: research_agent,
            agent_ids['writing']: writing_agent,
            agent_ids['review']: review_agent
        }
        
        # 在通信代理中注册所有代理
        log_agent_activity(project_id, 'communication', f'注册协作代理')
        for agent_type, agent_id in agent_ids.items():
            if agent_type != 'communication':
                communication_agent.register_agent(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    description=agents[agent_id].description if hasattr(agents[agent_id], 'description') else f"{agent_type.capitalize()} Agent"
                )
        
        # 初始化各阶段结果
        research_result = None
        paper_draft = None
        review_feedback = None
        final_paper = None
        
        # 记录每次迭代的版本ID
        version_history = {
            "research": [],
            "draft": [],
            "review": [],
            "final": []
        }
        
        # 迭代计数
        iteration = 0
        max_iterations = 3  # 防止无限循环
        
        # 错误计数
        error_count = 0
        max_errors = 3
        
        # 开始迭代流程
        while iteration < max_iterations:
            try:
                iteration += 1
                log_agent_activity(project_id, 'system', f'开始第 {iteration} 轮迭代')
                
                # 步骤1: 监督代理决定下一步操作
                log_agent_activity(project_id, 'supervisor', f'评估当前状态并分配任务')
                supervisor_decision = supervisor_agent.process(
                    project.topic, 
                    research_result, 
                    paper_draft, 
                    review_feedback
                )
                
                # 确保监督代理返回了有效的决策
                if not supervisor_decision or not isinstance(supervisor_decision, dict) or "action" not in supervisor_decision:
                    log_agent_activity(project_id, 'system', f'监督代理返回了无效的决策: {supervisor_decision}')
                    raise Exception(f"Invalid supervisor decision: {supervisor_decision}")
                
                log_agent_activity(project_id, 'supervisor', f'决定: {supervisor_decision["action"]}', 
                                details=supervisor_decision.get("reasoning", ""))
                
                # 步骤2: 根据监督代理的决定执行相应操作
                if supervisor_decision["action"] == "research":
                    # 研究阶段
                    log_agent_activity(project_id, 'supervisor', f'指示研究代理收集资料', 
                                      details=supervisor_decision.get("instructions", ""))
                    
                    # 监督代理向研究代理发送消息
                    communication_agent.send_message(
                        agent_ids['supervisor'],
                        agent_ids['research'],
                        f"请对主题'{project.topic}'进行研究。\n\n{supervisor_decision.get('instructions', '')}",
                        "task_assignment"
                    )
                    
                    log_agent_activity(project_id, 'research', f'开始收集与"{project.topic}"相关的论文')
                    research_result = research_agent.process(project.topic)
                    
                    # 研究代理向监督代理报告结果
                    communication_agent.send_message(
                        agent_ids['research'],
                        agent_ids['supervisor'],
                        f"我已完成关于'{project.topic}'的研究工作。",
                        "task_completion"
                    )
                    
                    # 将研究结果存储为一个版本
                    research_version = PaperVersion(
                        project_id=project_id,
                        version_number=iteration,
                        content_type='research',
                        content=research_result
                    )
                    db.session.add(research_version)
                    db.session.commit()
                    version_history["research"].append(research_version.id)
                    
                    log_agent_activity(project_id, 'research', f'研究完成，保存结果到版本ID:{research_version.id}')
                    
                elif supervisor_decision["action"] == "write":
                    # 写作阶段
                    is_revision = supervisor_decision.get("decision") == "revise"
                    
                    if is_revision:
                        log_agent_activity(project_id, 'supervisor', f'指示写作代理修改论文', 
                                        details=supervisor_decision.get("evaluation", ""))
                        
                        # 监督代理向写作代理发送修改指示
                        communication_agent.send_message(
                            agent_ids['supervisor'],
                            agent_ids['writing'],
                            f"请根据审阅意见修改'{project.topic}'论文。\n\n{supervisor_decision.get('evaluation', '')}",
                            "revision_request"
                        )
                        
                        # 获取最新的论文和审阅意见
                        latest_draft = PaperVersion.query.get(version_history["draft"][-1])
                        latest_review = PaperVersion.query.get(version_history["review"][-1])
                        
                        log_agent_activity(project_id, 'writing', f'开始根据审阅意见修改论文')
                        
                        # 处理审阅内容 - 如果存储为JSON字符串，解析为对象
                        review_content = latest_review.content
                        try:
                            # 尝试解析为JSON对象（如果是JSON字符串）
                            if isinstance(review_content, str) and (
                                review_content.startswith('[') or 
                                review_content.startswith('{')
                            ):
                                review_content = json.loads(review_content)
                        except json.JSONDecodeError:
                            # 如果不是有效的JSON，保持原样
                            logger.warning(f"审阅内容解析为JSON失败，使用原始内容")
                        
                        paper_draft = writing_agent.revise_draft(latest_draft.content, review_content)
                        
                        # 写作代理向审阅代理发送修改后的论文
                        communication_agent.send_message(
                            agent_ids['writing'],
                            agent_ids['review'],
                            f"我已根据您的审阅意见修改了论文。",
                            "revision_completed"
                        )
                        
                        # 写作代理向监督代理报告完成修改
                        communication_agent.send_message(
                            agent_ids['writing'],
                            agent_ids['supervisor'],
                            f"我已完成论文修改工作。",
                            "task_completion"
                        )
                    else:
                        log_agent_activity(project_id, 'supervisor', f'指示写作代理撰写论文', 
                                        details=supervisor_decision.get("instructions", ""))
                        
                        # 监督代理向写作代理发送写作指示
                        communication_agent.send_message(
                            agent_ids['supervisor'],
                            agent_ids['writing'],
                            f"请根据研究结果撰写关于'{project.topic}'的论文。\n\n{supervisor_decision.get('instructions', '')}",
                            "task_assignment"
                        )
                        
                        log_agent_activity(project_id, 'writing', f'开始撰写论文')
                        # 获取最新的研究结果
                        latest_research = PaperVersion.query.get(version_history["research"][-1])
                        paper_draft = writing_agent.process(project.topic, latest_research.content)
                        
                        # 写作代理向审阅代理发送完成的论文
                        communication_agent.send_message(
                            agent_ids['writing'],
                            agent_ids['review'],
                            f"我已完成'{project.topic}'论文的初稿。",
                            "draft_completed"
                        )
                        
                        # 写作代理向监督代理报告完成
                        communication_agent.send_message(
                            agent_ids['writing'],
                            agent_ids['supervisor'],
                            f"我已完成论文写作工作。",
                            "task_completion"
                        )
                    
                    # 将论文内容存储为一个版本
                    draft_version = PaperVersion(
                        project_id=project_id,
                        version_number=len(version_history["draft"]) + 1,
                        content_type='draft',
                        content=paper_draft
                    )
                    db.session.add(draft_version)
                    db.session.commit()
                    version_history["draft"].append(draft_version.id)
                    
                    log_agent_activity(project_id, 'writing', f'写作完成，保存结果到版本ID:{draft_version.id}')
                    
                elif supervisor_decision["action"] == "review":
                    # 审阅阶段
                    log_agent_activity(project_id, 'supervisor', f'指示审阅代理评估论文', 
                                      details=supervisor_decision.get("instructions", ""))
                    
                    # 监督代理向审阅代理发送审阅指示
                    communication_agent.send_message(
                        agent_ids['supervisor'],
                        agent_ids['review'],
                        f"请审阅关于'{project.topic}'的论文。\n\n{supervisor_decision.get('instructions', '')}",
                        "task_assignment"
                    )
                    
                    # 获取最新的论文草稿
                    latest_draft = PaperVersion.query.get(version_history["draft"][-1])
                    
                    log_agent_activity(project_id, 'review', f'开始审阅论文')
                    review_feedback = review_agent.process(project.topic, latest_draft.content)
                    
                    # 如果反馈不是字符串，将其转换为JSON字符串以便存储
                    if not isinstance(review_feedback, str):
                        review_feedback_str = json.dumps(review_feedback, ensure_ascii=False)
                    else:
                        review_feedback_str = review_feedback
                    
                    # 审阅代理向写作代理发送反馈
                    feedback_message = review_feedback
                    if isinstance(feedback_message, list):
                        feedback_message = "\n".join([f"- {item}" for item in feedback_message])
                    
                    communication_agent.send_message(
                        agent_ids['review'],
                        agent_ids['writing'],
                        f"我已完成论文审阅，有以下建议：\n\n{feedback_message}",
                        "review_feedback"
                    )
                    
                    # 审阅代理向监督代理报告完成
                    communication_agent.send_message(
                        agent_ids['review'],
                        agent_ids['supervisor'],
                        f"我已完成论文审阅工作。",
                        "task_completion"
                    )
                    
                    # 将审阅结果存储为一个版本
                    review_version = PaperVersion(
                        project_id=project_id,
                        version_number=len(version_history["review"]) + 1,
                        content_type='review',
                        content=review_feedback_str
                    )
                    db.session.add(review_version)
                    db.session.commit()
                    version_history["review"].append(review_version.id)
                    
                    log_agent_activity(project_id, 'review', f'审阅完成，保存结果到版本ID:{review_version.id}')
                    
                elif supervisor_decision["action"] == "complete":
                    # 完成论文
                    log_agent_activity(project_id, 'supervisor', f'确认论文完成', 
                                      details=supervisor_decision.get("evaluation", ""))
                    
                    # 获取最新的论文草稿作为最终版本
                    latest_draft = PaperVersion.query.get(version_history["draft"][-1])
                    final_paper = latest_draft.content
                    
                    # 监督代理向所有代理发送完成通知
                    for agent_type, agent_id in agent_ids.items():
                        if agent_type != 'supervisor' and agent_type != 'communication':
                            communication_agent.send_message(
                                agent_ids['supervisor'],
                                agent_id,
                                f"项目'{project.topic}'已完成。感谢您的贡献！",
                                "project_completion"
                            )
                    
                    # 将最终论文存储为一个版本
                    final_version = PaperVersion(
                        project_id=project_id,
                        version_number=len(version_history["final"]) + 1,
                        content_type='final',
                        content=final_paper
                    )
                    db.session.add(final_version)
                    db.session.commit()
                    version_history["final"].append(final_version.id)
                    
                    # 更新项目状态为已完成
                    project.status = "completed"
                    db.session.commit()
                    
                    log_agent_activity(project_id, 'system', f'项目完成，最终版本ID:{final_version.id}')
                    break
                
                # 在每轮结束后，让通信代理生成通信摘要
                if iteration > 0:
                    log_agent_activity(project_id, 'communication', f'生成第 {iteration} 轮协作通信摘要')
                    comm_summary = communication_agent.process(
                        request_type="generate_summary", 
                        topic=project.topic
                    )
                    try:
                        comm_summary_data = json.loads(comm_summary)
                        log_agent_activity(project_id, 'communication', f'通信摘要', 
                                          details=comm_summary_data.get('summary', '无法生成摘要'))
                    except:
                        log_agent_activity(project_id, 'communication', f'无法解析通信摘要')
                
                # 更新数据库
                db.session.commit()
            
            except Exception as e:
                error_count += 1
                logger.error(f"迭代 {iteration} 出错: {str(e)}")
                log_agent_activity(project_id, 'system', f'迭代 {iteration} 出错: {str(e)}')
                
                if error_count >= max_errors:
                    logger.error(f"达到最大错误次数 ({max_errors})，中止流程")
                    log_agent_activity(project_id, 'system', f'达到最大错误次数，中止流程')
                    project.status = "error"
                    db.session.commit()
                    
                    # 添加一条错误消息
                    message = AgentMessage(
                        project_id=project_id,
                        agent_type='system',
                        message_type='error',
                        message=f'多代理流程出现多次错误，已中止: {str(e)}'
                    )
                    db.session.add(message)
                    db.session.commit()
                    
                    return jsonify({
                        "status": "error",
                        "error": f"Multiple errors occurred: {str(e)}"
                    }), 500
                
                # 如果错误次数未达上限，继续下一轮迭代
                continue
        
        # 如果达到最大迭代次数但未完成，也标记为完成
        if iteration >= max_iterations and project.status != "completed":
            # 获取最新的论文草稿作为最终版本
            if version_history["draft"]:
                latest_draft = PaperVersion.query.get(version_history["draft"][-1])
                final_paper = latest_draft.content
                
                # 将最终论文存储为一个版本
                final_version = PaperVersion(
                    project_id=project_id,
                    version_number=len(version_history["final"]) + 1,
                    content_type='final',
                    content=final_paper
                )
                db.session.add(final_version)
                version_history["final"].append(final_version.id)
                
                # 更新项目状态为已完成
                project.status = "completed"
                db.session.commit()
                
                log_agent_activity(project_id, 'system', f'达到最大迭代次数，项目标记为完成，最终版本ID:{final_version.id}')
            else:
                project.status = "error"
                db.session.commit()
                log_agent_activity(project_id, 'system', f'达到最大迭代次数但无法生成最终论文，项目标记为错误')
        
        # 进行一次额外的协作总结
        log_agent_activity(project_id, 'communication', f'生成最终协作总结')
        try:
            collaboration_summary = communication_agent.facilitate_collaboration(
                project.topic,
                agents,
                max_rounds=1  # 只进行一轮总结性协作
            )
            
            if isinstance(collaboration_summary, str):
                collaboration_summary = json.loads(collaboration_summary)
                
            if collaboration_summary.get('success'):
                log_agent_activity(project_id, 'communication', f'协作总结', 
                                  details=collaboration_summary.get('summary', '无法生成协作总结'))
        except Exception as e:
            log_agent_activity(project_id, 'communication', f'生成协作总结时出错: {str(e)}')
        
        return jsonify({
            "status": "success",
            "message": "多代理交互式流程完成",
            "versions": version_history
        })
    except Exception as e:
        logger.error(f"多代理流程出错: {str(e)}")
        logger.error(traceback.format_exc())
        try:
            project.status = "error"
            db.session.commit()
            log_agent_activity(project_id, 'system', f'多代理流程出错: {str(e)}')
        except:
            pass
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=["GET"])
def api_logs():
    """获取应用日志的API"""
    try:
        log_file = "app.log"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.readlines()
            return jsonify({
                "status": "success",
                "logs": logs[-100:]  # 返回最后100行日志
            })
        else:
            return jsonify({
                "status": "success",
                "logs": ["No log file found"]
            })
    
    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/test-connection", methods=["GET"])
def api_test_connection():
    """Test connections to various APIs."""
    try:
        # 测试研究代理连接
        research_agent = get_research_agent()
        if research_agent:
            research_result = research_agent.test_connection()
        else:
            research_result = {"status": "error", "message": "研究代理初始化失败"}
        
        # 测试写作代理连接
        writing_agent = get_writing_agent()
        if writing_agent:
            writing_result = writing_agent.test_connection()
        else:
            writing_result = {"status": "error", "message": "写作代理初始化失败"}
        
        # 测试审阅代理连接
        review_agent = get_review_agent()
        if review_agent:
            review_result = review_agent.test_connection()
        else:
            review_result = {"status": "error", "message": "审阅代理初始化失败"}
            
        # 测试监督代理连接
        supervisor_agent = get_supervisor_agent()
        if supervisor_agent:
            supervisor_result = supervisor_agent.test_connection()
        else:
            supervisor_result = {"status": "error", "message": "监督代理初始化失败"}
        
        return jsonify({
            "status": "success",
            "research": research_result,
            "writing": writing_result,
            "review": review_result,
            "supervisor": supervisor_result
        })
    except Exception as e:
        logger.error(f"Error testing connections: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 静态文件服务
@app.route("/static/<path:path>")
def serve_static(path):
    """提供静态文件的API"""
    return send_from_directory("static", path)

# 版本保存和获取辅助函数
def save_version(project_id, content_type, content):
    """保存一个新的版本
    
    Args:
        project_id: 项目ID
        content_type: 内容类型 (research, draft, review, final)
        content: 内容
        
    Returns:
        保存的版本实例
    """
    # 获取当前该类型的最大版本号
    max_version = db.session.query(db.func.max(PaperVersion.version_number)) \
                  .filter_by(project_id=project_id, content_type=content_type).scalar() or 0
    
    # 创建新版本
    version = PaperVersion(
        project_id=project_id,
        content_type=content_type,
        version_number=max_version + 1,
        content=content
    )
    
    db.session.add(version)
    db.session.commit()
    
    return version

def get_latest_version_id(project_id, content_type):
    """获取指定项目和内容类型的最新版本ID
    
    Args:
        project_id: 项目ID
        content_type: 内容类型 (research, draft, review, final)
        
    Returns:
        最新版本ID，如果不存在则返回None
    """
    latest = PaperVersion.query \
            .filter_by(project_id=project_id, content_type=content_type) \
            .order_by(PaperVersion.version_number.desc()) \
            .first()
    
    return latest.id if latest else None

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)