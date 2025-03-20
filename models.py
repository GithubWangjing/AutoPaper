from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class PaperProject(db.Model):
    """Model for academic paper projects."""
    __tablename__ = 'paper_project'
    
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default="created")
    model_type = db.Column(db.String(50), default="siliconflow")
    research_source = db.Column(db.String(50), default="none")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 自定义模型配置
    custom_model_endpoint = db.Column(db.String(255), nullable=True)
    custom_model_api_key = db.Column(db.String(255), nullable=True)
    custom_model_name = db.Column(db.String(100), nullable=True)
    custom_model_temperature = db.Column(db.Float, nullable=True)
    custom_model_max_tokens = db.Column(db.Integer, nullable=True)
    
    # Track individual phases completion
    research_completed = db.Column(db.Boolean, default=False)
    writing_completed = db.Column(db.Boolean, default=False)
    review_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    versions = db.relationship('PaperVersion', backref='project', lazy=True, cascade='all, delete-orphan')
    agent_messages = db.relationship('AgentMessage', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def get_latest_version(self):
        """Get the most recent version of the paper."""
        return PaperVersion.query.filter_by(project_id=self.id).order_by(PaperVersion.created_at.desc()).first()
        
    def to_dict(self):
        """Convert project to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'topic': self.topic,
            'model_type': self.model_type,
            'research_source': self.research_source,
            'status': self.status,
            'research_completed': self.research_completed,
            'writing_completed': self.writing_completed,
            'review_completed': self.review_completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PaperVersion(db.Model):
    """Model to store different versions of the paper."""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('paper_project.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.String(50), nullable=True)  # agent type that created this version
    version_type = db.Column(db.String(50), default="draft")  # draft, revision, final, etc.
    content_type = db.Column(db.String(50), default="research")  # research, draft, review, final 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'content': self.content,
            'version_number': self.version_number,
            'created_by': self.created_by,
            'version_type': self.version_type,
            'content_type': self.content_type,
            'created_at': self.created_at.isoformat()
        }


class AgentMessage(db.Model):
    """Model to store messages in the agent conversation."""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('paper_project.id'), nullable=False)
    sender = db.Column(db.String(50), nullable=False)  # research_agent, writing_agent, review_agent
    receiver = db.Column(db.String(50), nullable=True)  # which agent this message is directed to
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default="text")  # text, suggestion, question, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'sender': self.sender,
            'receiver': self.receiver,
            'content': self.content,
            'message_type': self.message_type,
            'created_at': self.created_at.isoformat()
        } 