import os
import logging
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_file
from agents.research_agent import ResearchAgent
from agents.writing_agent import WritingAgent
from agents.review_agent import ReviewAgent
from utils import convert_markdown_to_html
from config import DEFAULT_MODEL_TYPE
from models import db, PaperProject, PaperVersion, AgentMessage
import time
import traceback
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from flask.cli import with_appcontext
import click
import markdown2
from io import BytesIO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///paper_projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with app
db.init_app(app)

# Initialize agents with the default model 
model_type = DEFAULT_MODEL_TYPE

# Initialize agents as None - will be created when needed
research_agent = None
writing_agent = None
review_agent = None

# Cache for agent instances
_agent_cache = {}

# 日志缓存，记录每个项目的代理工作日志
project_logs = {}

# 设置PDF支持标志
PDF_SUPPORT = False

# 尝试导入WeasyPrint，如果失败则将PDF支持设置为False
try:
    from weasyprint import HTML, CSS
    PDF_SUPPORT = True
except (ImportError, OSError) as e:
    logger.warning(f"WeasyPrint导入失败，PDF导出功能将不可用: {str(e)}")
    logger.warning("如需使用PDF功能，请安装GTK+库：https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows")

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

def init_db():
    """Initialize database and create all tables."""
    # First drop all tables if they exist
    logger.info("Dropping all existing tables...")
    db.drop_all()
    logger.info("All tables dropped.")
    
    # Then create new tables
    logger.info("Creating all tables...")
    db.create_all()
    logger.info("Database tables created successfully:"
                + str([table.name for table in db.metadata.sorted_tables]))

# 替换before_first_request为Flask 2.0+兼容的方式
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database tables."""
    init_db()
    click.echo('Initialized the database.')

# 注册命令和初始化应用
def init_app(app):
    app.cli.add_command(init_db_command)
    # 确保应用启动时初始化数据库
    with app.app_context():
        init_db()

# 调用初始化
init_app(app)

def get_research_agent():
    """Create and return a research agent."""
    model_type = os.getenv("DEFAULT_MODEL_TYPE", "siliconflow")
    return ResearchAgent(model_type=model_type)

def get_writing_agent():
    global writing_agent
    cache_key = f"writing_{model_type}"
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]
    if writing_agent is None:
        writing_agent = WritingAgent(model_type=model_type)
        _agent_cache[cache_key] = writing_agent
    return writing_agent

def get_review_agent():
    global review_agent
    cache_key = f"review_{model_type}"
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]
    if review_agent is None:
        review_agent = ReviewAgent(model_type=model_type)
        _agent_cache[cache_key] = review_agent
    return review_agent

# Valid configuration options
VALID_MODEL_TYPES = ['openai', 'siliconflow']

@app.route('/')
def index():
    """Main landing page showing projects."""
    with app.app_context():
        projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/verify-model', methods=['POST'])
def verify_model():
    """Verify if a model configuration is valid and accessible."""
    try:
        data = request.json
        model_type = data.get('model_type', DEFAULT_MODEL_TYPE)
        
        logger.info(f"Verifying model: {model_type}")

        if model_type not in VALID_MODEL_TYPES:
            return jsonify({'status': 'error', 'message': 'Invalid model type'}), 400
            
        # Create a temporary agent to verify connectivity
        try:
            temp_agent = ResearchAgent(model_type=model_type)
            # Make a minimal API call to verify connectivity
            test_result = temp_agent.test_connection()
            if test_result.get('status') == 'success':
                return jsonify({'status': 'success', 'message': 'Model configuration verified successfully'})
            else:
                return jsonify({'status': 'error', 'message': test_result.get('message', 'Unknown error')}), 400
        except Exception as e:
            logger.error(f"Error verifying model: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 400

    except Exception as e:
        logger.error(f"Error in verify-model: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/set-model', methods=['POST'])
def set_model():
    """Change the model type used by the agents."""
    try:
        data = request.json
        new_model_type = data.get('model_type', DEFAULT_MODEL_TYPE)

        logger.info(f"Setting model type to: {new_model_type}")

        if new_model_type not in VALID_MODEL_TYPES:
            return jsonify({'error': 'Invalid model type'}), 400

        global model_type, research_agent, writing_agent, review_agent, _agent_cache
        
        # Clear the agent cache when model type changes
        _agent_cache.clear()
        
        model_type = new_model_type
        
        # Create new agents with updated configuration
        research_agent = ResearchAgent(model_type=model_type)
        writing_agent = WritingAgent(model_type=model_type)
        review_agent = ReviewAgent(model_type=model_type)

        return jsonify({'status': 'success', 'model': model_type})
    except Exception as e:
        logger.error(f"Error setting model: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/projects', methods=['GET'])
def list_projects():
    """Get a list of all projects."""
    try:
        with app.app_context():
            projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
            return jsonify({
                'status': 'success',
                'projects': [project.to_dict() for project in projects]
            })
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project and its details."""
    try:
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            versions = PaperVersion.query.filter_by(project_id=project_id).order_by(PaperVersion.version_number.desc()).all()
            messages = AgentMessage.query.filter_by(project_id=project_id).order_by(AgentMessage.created_at).all()
            
            return render_template(
                'project_detail.html', 
                project=project, 
                versions=versions, 
                messages=messages,
                latest_version=versions[0] if versions else None
            )
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/projects', methods=['POST'])
def create_project():
    """Create a new paper project."""
    try:
        data = request.json
        topic = data.get('topic')
        selected_model = data.get('model_type', DEFAULT_MODEL_TYPE)
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        # Validate model type
        if selected_model not in VALID_MODEL_TYPES:
            return jsonify({'error': 'Invalid model type'}), 400
            
        # Set the model for agents
        global research_agent, writing_agent, review_agent
        if selected_model != model_type:
            try:
                research_agent = ResearchAgent(model_type=selected_model)
                writing_agent = WritingAgent(model_type=selected_model)
                review_agent = ReviewAgent(model_type=selected_model)
                logger.info(f"Model changed to {selected_model} for new project")
            except Exception as e:
                logger.error(f"Failed to set model for new project: {str(e)}")
                # Continue with project creation, but log the error

        with app.app_context():
            # Create a new project with model info
            project = PaperProject(
                topic=topic, 
                model_type=selected_model
            )
            db.session.add(project)
            db.session.commit()
            
            # Start the interactive paper generation process asynchronously
            # Note: In a production app, this would be handled by a task queue like Celery
            project_id = project.id
            
            # Redirect to project detail page
            return jsonify({
                'status': 'success',
                'project_id': project_id,
                'redirect_url': f'/projects/{project_id}'
            })
            
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-interactive-paper/<int:project_id>', methods=['POST'])
def generate_interactive_paper(project_id):
    """Start the interactive paper generation process."""
    try:
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            topic = project.topic
            
            # Step 1: Research Agent gathers information
            logger.info(f"Starting research phase for topic: {topic}")
            
            # Add a message from research agent
            research_start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content=f"Starting research on topic: '{topic}'",
                message_type="status"
            )
            db.session.add(research_start_msg)
            db.session.commit()
            
            # Make the research agent's API call
            try:
                research_results = get_research_agent().process(topic)
        try:
            research_data = json.loads(research_results)
            research_content = research_data.get('content', research_results)
        except json.JSONDecodeError:
            research_content = research_results
            except Exception as e:
                # Handle API errors gracefully
                error_msg = str(e)
                logger.error(f"Research API error: {error_msg}")
                research_error = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error during research phase: {error_msg}",
                    message_type="error"
                )
                db.session.add(research_error)
                db.session.commit()
                
                # Update project status
                project.status = "failed"
                db.session.commit()
                return jsonify({'status': 'error', 'error': error_msg}), 500
                
            # Add the research results as a message
            research_msg = AgentMessage(
                project_id=project_id,
                sender="research_agent",
                receiver="writing_agent",
                content=research_content,
                message_type="research_results"
            )
            db.session.add(research_msg)
            db.session.commit()
            
            # Step 2: Writing Agent creates a draft
        logger.info("Starting writing phase...")
            
            # Add a message from writing agent
            writing_start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content="Starting to write the initial draft based on research findings",
                message_type="status"
            )
            db.session.add(writing_start_msg)
            db.session.commit()
            
            # Make the writing agent's API call
            try:
                paper_draft = get_writing_agent().process(topic, research_content)
        try:
            draft_data = json.loads(paper_draft)
            draft_content = draft_data.get('content', paper_draft)
        except json.JSONDecodeError:
            draft_content = paper_draft
            except Exception as e:
                # Handle API errors gracefully
                error_msg = str(e)
                logger.error(f"Writing API error: {error_msg}")
                writing_error = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error during writing phase: {error_msg}",
                    message_type="error"
                )
                db.session.add(writing_error)
                db.session.commit()
                
                # Update project status
                project.status = "failed"
                db.session.commit()
                return jsonify({'status': 'error', 'error': error_msg}), 500
                
            # Save the first draft as a version
            draft_version = PaperVersion(
                project_id=project_id,
                content=draft_content,
                version_number=1,
                created_by="writing_agent"
            )
            db.session.add(draft_version)
            
            # Add the draft as a message
            draft_msg = AgentMessage(
                project_id=project_id,
                sender="writing_agent",
                receiver="review_agent",
                content="I've created an initial draft based on the research findings.",
                message_type="notification"
            )
            db.session.add(draft_msg)
            db.session.commit()
            
            # Step 3: Review Agent provides feedback
        logger.info("Starting review phase...")
            
            # Add a message from review agent
            review_start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content="Starting the review process on the initial draft",
                message_type="status"
            )
            db.session.add(review_start_msg)
            db.session.commit()
            
            # Make the review agent's API call for feedback
            try:
                review_feedback = get_review_agent().provide_feedback(draft_content)
                try:
                    feedback_data = json.loads(review_feedback)
                    feedback_content = feedback_data.get('feedback', review_feedback)
                except json.JSONDecodeError:
                    feedback_content = review_feedback
            except Exception as e:
                # Handle API errors gracefully
                error_msg = str(e)
                logger.error(f"Review API error: {error_msg}")
                review_error = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error during review phase: {error_msg}",
                    message_type="error"
                )
                db.session.add(review_error)
                db.session.commit()
                
                # Update project status
                project.status = "failed"
                db.session.commit()
                return jsonify({'status': 'error', 'error': error_msg}), 500
                
            # Add the feedback as a message
            feedback_msg = AgentMessage(
                project_id=project_id,
                sender="review_agent",
                receiver="writing_agent",
                content=feedback_content,
                message_type="feedback"
            )
            db.session.add(feedback_msg)
            db.session.commit()
            
            # Step 4: Writing Agent makes revisions based on feedback
            logger.info("Starting revision phase...")
            
            # Add a message from writing agent
            revision_start_msg = AgentMessage(
                project_id=project_id,
                sender="system", 
                content="Writing agent is revising the draft based on review feedback",
                message_type="status"
            )
            db.session.add(revision_start_msg)
            db.session.commit()
            
            # Make the writing agent's API call for revision
            try:
                revised_draft = get_writing_agent().revise_draft(draft_content, feedback_content)
                try:
                    revised_data = json.loads(revised_draft)
                    revised_content = revised_data.get('revised_paper', revised_draft)
                    revision_summary = revised_data.get('revision_summary', {})
                except json.JSONDecodeError:
                    revised_content = revised_draft
                    revision_summary = {}
            except Exception as e:
                # Handle API errors gracefully
                error_msg = str(e)
                logger.error(f"Revision API error: {error_msg}")
                revision_error = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error during revision phase: {error_msg}",
                    message_type="error"
                )
                db.session.add(revision_error)
                db.session.commit()
                
                # Update project status
                project.status = "failed"
                db.session.commit()
                return jsonify({'status': 'error', 'error': error_msg}), 500
                
            # Evaluate the revision quality
            try:
                evaluation = get_review_agent().evaluate_revision(draft_content, revised_content, feedback_content)
                evaluation_data = json.loads(evaluation)
                improvement_score = evaluation_data.get('evaluation', {}).get('quality_assessment', {}).get('improvement_score', '0')
                
                # Add evaluation message
                evaluation_msg = AgentMessage(
                    project_id=project_id,
                    sender="review_agent",
                    receiver="writing_agent",
                    content=f"Revision evaluation: Improvement score {improvement_score}/10",
                    message_type="evaluation"
                )
                db.session.add(evaluation_msg)
                
                # If improvement score is too low, request another revision
                if int(improvement_score) < 7:
                    revision_request = AgentMessage(
                        project_id=project_id,
                        sender="review_agent",
                        receiver="writing_agent",
                        content="The revision needs further improvement. Please address the remaining concerns.",
                        message_type="revision_request"
                    )
                    db.session.add(revision_request)
                    db.session.commit()
                    
                    # Make another revision attempt
                    revised_draft = get_writing_agent().revise_draft(revised_content, evaluation_data.get('evaluation', {}).get('remaining_concerns', []))
                    try:
                        revised_data = json.loads(revised_draft)
                        revised_content = revised_data.get('revised_paper', revised_draft)
                    except json.JSONDecodeError:
                        revised_content = revised_draft
            except Exception as e:
                logger.error(f"Evaluation error: {str(e)}")
                # Continue with the current revision if evaluation fails
                
            # Save the revised draft as a new version
            revised_version = PaperVersion(
                project_id=project_id,
                content=revised_content,
                version_number=2,
                created_by="writing_agent"
            )
            db.session.add(revised_version)
            
            # Add the revised draft as a message
            revision_msg = AgentMessage(
                project_id=project_id,
                sender="writing_agent",
                receiver="review_agent",
                content="I've revised the draft based on your feedback.",
                message_type="notification"
            )
            db.session.add(revision_msg)
            db.session.commit()
            
            # Step 5: Final review and polish
            logger.info("Starting final review phase...")
            
            # Add a message from review agent
            final_review_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content="Performing final review and polish",
                message_type="status"
            )
            db.session.add(final_review_msg)
            db.session.commit()
            
            # Make the review agent's API call for final polish
            try:
                final_paper = get_review_agent().final_polish(revised_content)
                try:
                    final_data = json.loads(final_paper)
                    final_content = final_data.get('content', final_paper)
                except json.JSONDecodeError:
                    final_content = final_paper
                except Exception as e:
                    # Handle API errors gracefully
                    error_msg = str(e)
                    logger.error(f"Final polish API error: {error_msg}")
                    polish_error = AgentMessage(
                        project_id=project_id,
                        sender="system",
                        content=f"Error during final polish phase: {error_msg}",
                        message_type="error"
                    )
                    db.session.add(polish_error)
                    db.session.commit()
                    
                    # Update project status
                    project.status = "failed"
                    db.session.commit()
                    return jsonify({'status': 'error', 'error': error_msg}), 500
                
            except Exception as e:
                # Handle API errors gracefully
                error_msg = str(e)
                logger.error(f"Final polish API error: {error_msg}")
                polish_error = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error during final polish phase: {error_msg}",
                    message_type="error"
                )
                db.session.add(polish_error)
                db.session.commit()
                
                # Update project status
                project.status = "failed"
                db.session.commit()
                return jsonify({'status': 'error', 'error': error_msg}), 500
                
            # Save the final paper as a new version
            final_version = PaperVersion(
                project_id=project_id,
                content=final_content,
                version_number=3,
                created_by="review_agent"
            )
            db.session.add(final_version)
            
            # Add the final paper completion message
            completion_msg = AgentMessage(
                project_id=project_id,
                sender="review_agent",
                receiver=None,
                content="The paper has been finalized after collaborative revisions.",
                message_type="completion"
            )
            db.session.add(completion_msg)
            
            # Update project status
            project.status = "completed"
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Interactive paper generation completed',
                'project_id': project_id
            })
            
    except Exception as e:
        logger.error(f"Error in interactive paper generation: {str(e)}")
        logger.error(traceback.format_exc())
        with app.app_context():
            # Update project status to failed
            project = PaperProject.query.get(project_id)
            if project:
                project.status = "failed"
                
                # Add error message
                error_msg = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=f"Error generating paper: {str(e)}",
                    message_type="error"
                )
                db.session.add(error_msg)
                db.session.commit()
                
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/progress/<int:project_id>', methods=['GET'])
def get_project_progress(project_id):
    """Get progress information for a specific project."""
    try:
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            
            # Get the latest message timestamp and count
            latest_message = AgentMessage.query.filter_by(project_id=project_id).order_by(AgentMessage.created_at.desc()).first()
            message_count = AgentMessage.query.filter_by(project_id=project_id).count()
            
            # Get the latest version
            latest_version = PaperVersion.query.filter_by(project_id=project_id).order_by(PaperVersion.version_number.desc()).first()
            
            progress_data = {
                'status': project.status,
                'message_count': message_count,
                'latest_message': latest_message.to_dict() if latest_message else None,
                'latest_version': latest_version.to_dict() if latest_version else None,
                'research_progress': get_research_agent().get_progress(),
                'writing_progress': get_writing_agent().get_progress(),
                'review_progress': get_review_agent().get_progress()
            }
            
            return jsonify(progress_data)
    except Exception as e:
        logger.error(f"Error getting project progress: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<int:project_id>/status', methods=['GET'])
def get_project_status(project_id):
    project = PaperProject.query.get_or_404(project_id)
    return jsonify({
        'status': project.status,
        'model_type': project.model_type,
        'research_source': project.research_source,
        'created_at': project.created_at.isoformat(),
        'updated_at': project.updated_at.isoformat()
    })

@app.route('/projects/<int:project_id>/pause', methods=['POST'])
def pause_project(project_id):
    project = PaperProject.query.get_or_404(project_id)
    if project.status == 'in_progress':
        project.status = 'paused'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Project paused successfully'})
    return jsonify({'status': 'error', 'message': 'Project is not in progress'}), 400

@app.route('/projects/<int:project_id>/resume', methods=['POST'])
def resume_project(project_id):
    project = PaperProject.query.get_or_404(project_id)
    if project.status == 'paused':
        project.status = 'in_progress'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Project resumed successfully'})
    return jsonify({'status': 'error', 'message': 'Project is not paused'}), 400

@app.route('/projects/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    project = PaperProject.query.get_or_404(project_id)
    try:
        # Delete all related versions and messages
        PaperVersion.query.filter_by(project_id=project_id).delete()
        AgentMessage.query.filter_by(project_id=project_id).delete()
        db.session.delete(project)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Project deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Legacy route for backward compatibility
@app.route('/generate-paper', methods=['POST'])
def generate_paper():
    """Legacy route that creates a project and redirects to the new interactive workflow."""
    try:
        data = request.json
        topic = data.get('topic')
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        with app.app_context():
            # Create a new project
            project = PaperProject(topic=topic)
            db.session.add(project)
            db.session.commit()
            
            # Start the interactive paper generation process
            project_id = project.id
            
            # Call the new interactive generation endpoint
            response = generate_interactive_paper(project_id)
            
            html_content = ""
            if isinstance(response, tuple):
                # If there was an error
                return response
            else:
                # If success, get the final version HTML
                with app.app_context():
                    final_version = PaperVersion.query.filter_by(
                        project_id=project_id
                    ).order_by(PaperVersion.version_number.desc()).first()
                    
                    if final_version:
                        html_content = convert_markdown_to_html(final_version.content)

        return jsonify({
            'status': 'success',
                'paper': html_content,
                'project_id': project_id
        })

    except Exception as e:
        logger.error(f"Error generating paper: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress', methods=['GET'])
def get_progress():
    """Legacy route for getting progress information."""
    # Get progress status from each agent
    progress = {
        'research': get_research_agent().get_progress(),
        'writing': get_writing_agent().get_progress(),
        'review': get_review_agent().get_progress()
    }
    return jsonify(progress)

@app.route('/api/projects', methods=['GET'])
def api_list_projects():
    """API endpoint to get a list of all projects."""
    try:
        with app.app_context():
            projects = PaperProject.query.order_by(PaperProject.updated_at.desc()).all()
            return jsonify([project.to_dict() for project in projects])
    except Exception as e:
        logger.error(f"Error listing projects via API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """API endpoint to create a new paper project."""
    try:
        data = request.json
        title = data.get('title')
        selected_model = data.get('model_type', DEFAULT_MODEL_TYPE)
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        # Validate model type
        if selected_model not in VALID_MODEL_TYPES:
            return jsonify({'error': 'Invalid model type'}), 400
            
        # Update global model configuration if different
        global model_type
        if selected_model != model_type:
            model_type = selected_model
            # Clear the agent cache
            _agent_cache.clear()

        with app.app_context():
            # Create a new project
            project = PaperProject(
                topic=title,  # Use title as topic
                model_type=selected_model,
                status='created'  # Initial status
            )
            db.session.add(project)
            db.session.commit()
            
            # Return the created project
            return jsonify(project.to_dict())
            
    except Exception as e:
        logger.error(f"Error creating project via API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    """API endpoint to get a specific project's details."""
    try:
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            return jsonify(project.to_dict())
    except Exception as e:
        logger.error(f"Error getting project via API: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/projects/<int:project_id>/start-research', methods=['POST'])
def api_start_research(project_id):
    """API endpoint to start the research phase for a project."""
    try:
        logger.info(f"Starting research phase for project ID: {project_id}")
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            logger.info(f"Found project: {project.topic}, current status: {project.status}")
            
            # Update project status
            project.status = 'researching'
            db.session.commit()
            logger.info(f"Updated project status to: {project.status}")
            
            # Get or create research agent with project-specific model and research source
            research_agent = get_research_agent()
            
            # Record start message
            start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content=f"Starting research on: {project.topic}",
                message_type="status"
            )
            db.session.add(start_msg)
            db.session.commit()
            
            # Store project data to pass to thread
            project_topic = project.topic
            
            # Start research in a background thread to not block the API response
            def run_research():
                with app.app_context():  # Ensure thread has app context
                    try:
                        logger.info(f"Executing research for project {project_id} on topic: {project_topic}")
                        log_agent_activity(project_id, "research_agent", "开始研究", project_topic)
                        
                        # Perform actual research
                        log_agent_activity(project_id, "research_agent", "搜索相关论文")
                        research_results = research_agent.process(project_topic)
                        
                        # Parse research results
                        try:
                            research_data = json.loads(research_results)
                            log_agent_activity(project_id, "research_agent", f"找到 {len(research_data.get('papers', []))} 篇相关论文")
                        except json.JSONDecodeError:
                            research_data = {"content": research_results}
                            log_agent_activity(project_id, "research_agent", "完成研究")
                        
                        # Save research results to database
                        log_agent_activity(project_id, "research_agent", "保存研究结果")
                        research_complete_msg = AgentMessage(
                            project_id=project_id,
                            sender="research_agent",
                            content=json.dumps(research_data),
                            message_type="research_results"
                        )
                        db.session.add(research_complete_msg)
                        
                        # Update project with research completion
                        project = PaperProject.query.get(project_id)
                        project.research_completed = True
                        project.status = 'research_completed'
                        db.session.commit()
                        
                        log_agent_activity(project_id, "research_agent", "研究阶段完成")
                        logger.info(f"Research completed for project {project_id}")
                    except Exception as e:
                        error_msg = f"Error in research process: {str(e)}"
                        logger.error(error_msg)
                        logger.error(traceback.format_exc())
                        
                        log_agent_activity(project_id, "research_agent", "研究过程中出错", str(e))
                        
                        # Record error
                        error_message = AgentMessage(
                            project_id=project_id,
                            sender="system",
                            content=error_msg,
                            message_type="error"
                        )
                        db.session.add(error_message)
                        
                        # Update project status to reflect error
                        project = PaperProject.query.get(project_id)
                        project.status = 'research_failed'
                        db.session.commit()
            
            # Start research in background thread
            import threading
            research_thread = threading.Thread(target=run_research)
            research_thread.daemon = True
            research_thread.start()
            
            return jsonify({'status': 'success', 'message': 'Research started', 'project_id': project_id})
    except Exception as e:
        logger.error(f"Error starting research: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-writing', methods=['POST'])
def api_start_writing(project_id):
    """API endpoint to start the writing phase for a project."""
    try:
        logger.info(f"Starting writing phase for project ID: {project_id}")
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            logger.info(f"Found project: {project.topic}, current status: {project.status}")
            
            # Update project status
            project.status = 'writing'
            db.session.commit()
            logger.info(f"Updated project status to: {project.status}")
            
            # Get or create writing agent with project-specific model
            writing_agent = get_writing_agent()
            
            # Record start message
            start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content=f"Starting paper writing for: {project.topic}",
                message_type="status"
            )
            db.session.add(start_msg)
            db.session.commit()
            
            # Store project data to pass to thread
            project_topic = project.topic
            
            # Get research results if available
            research_results = AgentMessage.query.filter_by(
                project_id=project_id, 
                message_type="research_results"
            ).order_by(AgentMessage.created_at.desc()).first()
            
            if not research_results:
                # Create dummy research if none exists
                logger.warning(f"No research results found for project {project_id}. Creating synthetic research.")
                research_data = {"synthetic": True, "topic": project_topic}
            else:
                try:
                    research_data = json.loads(research_results.content)
                except json.JSONDecodeError:
                    research_data = {"content": research_results.content}
            
            # Convert research_data to JSON string to pass to thread
            research_data_json = json.dumps(research_data)
            
            # Start writing in a background thread to not block the API response
            def run_writing():
                with app.app_context():  # Ensure thread has app context
                    try:
                        logger.info(f"Executing writing for project {project_id} on topic: {project_topic}")
                        log_agent_activity(project_id, "writing_agent", "开始撰写论文", project_topic)
                        
                        # Perform actual paper writing
                        log_agent_activity(project_id, "writing_agent", "分析研究结果")
                        paper_content = writing_agent.process(project_topic, research_data_json)
                        
                        # Save paper version to database
                        log_agent_activity(project_id, "writing_agent", "生成初稿")
                        new_version = PaperVersion(
                            project_id=project_id,
                            version_number=1,  # First version
                            content=paper_content,
                            version_type="initial_draft"
                        )
                        db.session.add(new_version)
                        
                        # Add completion message
                        log_agent_activity(project_id, "writing_agent", "完成论文初稿")
                        writing_complete_msg = AgentMessage(
                            project_id=project_id,
                            sender="writing_agent",
                            content="Paper draft completed",
                            message_type="status"
                        )
                        db.session.add(writing_complete_msg)
                        
                        # Update project with writing completion
                        project = PaperProject.query.get(project_id)
                        project.writing_completed = True
                        project.status = 'writing_completed'
                        db.session.commit()
                        
                        log_agent_activity(project_id, "writing_agent", "写作阶段完成")
                        logger.info(f"Writing completed for project {project_id}")
                    except Exception as e:
                        error_msg = f"Error in writing process: {str(e)}"
                        logger.error(error_msg)
                        logger.error(traceback.format_exc())
                        
                        log_agent_activity(project_id, "writing_agent", "写作过程中出错", str(e))
                        
                        # Record error
                        error_message = AgentMessage(
                            project_id=project_id,
                            sender="system",
                            content=error_msg,
                            message_type="error"
                        )
                        db.session.add(error_message)
                        
                        # Update project status to reflect error
                        project = PaperProject.query.get(project_id)
                        project.status = 'writing_failed'
                        db.session.commit()
            
            # Start writing in background thread
            import threading
            writing_thread = threading.Thread(target=run_writing)
            writing_thread.daemon = True
            writing_thread.start()
            
            return jsonify({'status': 'success', 'message': 'Writing started', 'project_id': project_id})
    except Exception as e:
        logger.error(f"Error starting writing: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/start-review', methods=['POST'])
def api_start_review(project_id):
    """API endpoint to start the review phase for a project."""
    try:
        logger.info(f"Starting review phase for project ID: {project_id}")
        with app.app_context():
            project = PaperProject.query.get_or_404(project_id)
            logger.info(f"Found project: {project.topic}, current status: {project.status}")
            
            # Update project status
            project.status = 'reviewing'
            db.session.commit()
            logger.info(f"Updated project status to: {project.status}")
            
            # Get or create review agent with project-specific model
            review_agent = get_review_agent()
            
            # Record start message
            start_msg = AgentMessage(
                project_id=project_id,
                sender="system",
                content=f"Starting paper review for: {project.topic}",
                message_type="status"
            )
            db.session.add(start_msg)
            db.session.commit()
            
            # Store project data to pass to thread
            project_topic = project.topic
            
            # Get latest paper version if available
            paper_version = PaperVersion.query.filter_by(
                project_id=project_id
            ).order_by(PaperVersion.version_number.desc()).first()
            
            if not paper_version:
                # Error if no paper version exists
                error_msg = f"No paper version found for project {project_id}"
                logger.error(error_msg)
                
                error_message = AgentMessage(
                    project_id=project_id,
                    sender="system",
                    content=error_msg,
                    message_type="error"
                )
                db.session.add(error_message)
                
                # Update project status
                project.status = 'review_failed'
                db.session.commit()
                
                return jsonify({'status': 'error', 'error': error_msg}), 400
            
            # Store paper content to pass to thread
            paper_content = paper_version.content
            
            # Start review in a background thread to not block the API response
            def run_review():
                with app.app_context():  # Ensure thread has app context
                    try:
                        logger.info(f"Executing review for project {project_id}")
                        log_agent_activity(project_id, "review_agent", "开始审阅论文")
                        
                        # Perform actual paper review
                        log_agent_activity(project_id, "review_agent", "分析论文内容和结构")
                        review_results = review_agent.provide_feedback(paper_content)
                        
                        # Save review results to database
                        log_agent_activity(project_id, "review_agent", "生成审阅意见")
                        review_msg = AgentMessage(
                            project_id=project_id,
                            sender="review_agent",
                            content=json.dumps(review_results) if isinstance(review_results, dict) else review_results,
                            message_type="review_results"
                        )
                        db.session.add(review_msg)
                        
                        # Perform final polish based on review
                        try:
                            log_agent_activity(project_id, "review_agent", "进行最终润色")
                            final_paper = review_agent.final_polish(paper_content)
                            
                            # Save final paper version
                            log_agent_activity(project_id, "review_agent", "保存最终版本")
                            final_version = PaperVersion(
                                project_id=project_id,
                                version_number=paper_version.version_number + 1,
                                content=final_paper,
                                version_type="final_version",
                                created_by="review_agent"
                            )
                            db.session.add(final_version)
                            
                            # Add completion message
                            log_agent_activity(project_id, "review_agent", "完成论文终稿")
                            completion_msg = AgentMessage(
                                project_id=project_id,
                                sender="review_agent",
                                content="Paper has been reviewed and finalized",
                                message_type="completion"
                            )
                            db.session.add(completion_msg)
                            
                            # Update project with review completion
                            project = PaperProject.query.get(project_id)
                            project.review_completed = True
                            project.status = 'completed'
                            db.session.commit()
                            
                            log_agent_activity(project_id, "review_agent", "审阅阶段完成")
                            logger.info(f"Review completed for project {project_id}")
                        except Exception as polish_e:
                            # If final polish fails, mark review as complete but note the error
                            logger.error(f"Error in final polish: {str(polish_e)}")
                            log_agent_activity(project_id, "review_agent", "最终润色时出错", str(polish_e))
                            
                            error_message = AgentMessage(
                                project_id=project_id,
                                sender="system",
                                content=f"Error in final polish: {str(polish_e)}",
                                message_type="error"
                            )
                            db.session.add(error_message)
                            
                            # Still mark review as complete
                            project = PaperProject.query.get(project_id)
                            project.review_completed = True
                            project.status = 'completed'
                            db.session.commit()
                            
                    except Exception as e:
                        error_msg = f"Error in review process: {str(e)}"
                        logger.error(error_msg)
                        logger.error(traceback.format_exc())
                        
                        log_agent_activity(project_id, "review_agent", "审阅过程中出错", str(e))
                        
                        # Record error
                        error_message = AgentMessage(
                            project_id=project_id,
                            sender="system",
                            content=error_msg,
                            message_type="error"
                        )
                        db.session.add(error_message)
                        
                        # Update project status to reflect error
                        project = PaperProject.query.get(project_id)
                        project.status = 'review_failed'
                        db.session.commit()
            
            # Start review in background thread
            import threading
            review_thread = threading.Thread(target=run_review)
            review_thread.daemon = True
            review_thread.start()
            
            return jsonify({'status': 'success', 'message': 'Review started', 'project_id': project_id})
    except Exception as e:
        logger.error(f"Error starting review: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/versions/<int:version_id>', methods=['GET'])
def api_get_version(version_id):
    """API endpoint to get a specific paper version."""
    try:
        with app.app_context():
            version = PaperVersion.query.get_or_404(version_id)
            return jsonify(version.to_dict())
    except Exception as e:
        logger.error(f"Error getting version via API: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/export', methods=['GET'])
def api_export_paper(project_id):
    """Export a paper in HTML or PDF format"""
    try:
        # 获取请求的导出格式，默认为HTML
        export_format = request.args.get('format', 'html').lower()
        
        # 如果请求PDF但不支持，返回警告并强制使用HTML
        if export_format == 'pdf' and not PDF_SUPPORT:
            logger.warning("PDF导出被请求，但系统不支持PDF生成。将回退到HTML格式。")
            export_format = 'html'
        
        # 获取项目
        project = PaperProject.query.get_or_404(project_id)
        
        # 获取最新版本的论文
        paper_version = PaperVersion.query.filter_by(
            project_id=project_id
        ).order_by(PaperVersion.version_number.desc()).first()
        
        if not paper_version:
            return jsonify({'status': 'error', 'error': 'No paper version found'}), 404
        
        # 将Markdown转换为HTML
        html_content = markdown2.markdown(paper_version.content)
        
        # 创建完整的HTML文档，包含样式
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
        
        # 根据请求的格式返回HTML或PDF
        if export_format == 'html':
            # 返回HTML
            return Response(
                styled_html,
                mimetype='text/html',
                headers={'Content-Disposition': f'attachment; filename={project.topic}.html'}
            )
        elif export_format == 'pdf' and PDF_SUPPORT:
            try:
                # 尝试生成PDF
                pdf = HTML(string=styled_html).write_pdf()
                
                # 返回PDF
                return send_file(
                    BytesIO(pdf),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"{project.topic}.pdf"
                )
            except Exception as e:
                # 如果PDF生成失败，记录错误并返回HTML
                logger.error(f"PDF生成失败: {str(e)}")
                logger.info("回退到HTML格式")
                
                return Response(
                    styled_html,
                    mimetype='text/html',
                    headers={'Content-Disposition': f'attachment; filename={project.topic}.html'}
                )
        else:
            # 不支持的格式
            return jsonify({'status': 'error', 'error': 'Unsupported format'}), 400
    except Exception as e:
        logger.error(f"导出论文发生错误: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

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
                filtered_logs = [log for log in logs if log['timestamp'] > since_timestamp]
                return jsonify(filtered_logs)
            else:
                return jsonify(logs)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"Error getting project logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/status', methods=['GET'])
def api_project_status(project_id):
    """Get the status of a project by ID."""
    try:
        # Use get() instead of get_or_404() to handle the error explicitly
        project = PaperProject.query.get(project_id)
        if not project:
            logger.warning(f"Project with ID {project_id} not found")
            return jsonify({"status": "error", "message": f"Project with ID {project_id} not found"}), 404
        
        # Return a simpler status response
        return jsonify({
            "id": project.id,
            "topic": project.topic,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "completed": {
                "research": project.research_completed,
                "writing": project.writing_completed,
                "review": project.review_completed
            }
        })
    except Exception as e:
        logger.error(f"Error getting project status: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)