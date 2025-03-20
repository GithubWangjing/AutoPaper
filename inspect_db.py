import sqlite3
import os
import logging
from sqlalchemy import create_engine, inspect
from models import PaperVersion, PaperProject, db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_database():
    # Get the database path
    db_path = os.path.join('instance', 'paper_projects.db')
    
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}")
        return
    
    logger.info(f"Inspecting database at {db_path}")
    
    try:
        # Using SQLite directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Tables in database: {[table[0] for table in tables]}")
        
        # Inspect paper_version table
        cursor.execute("PRAGMA table_info(paper_version)")
        columns = cursor.fetchall()
        
        logger.info("paper_version table schema:")
        for col in columns:
            logger.info(f"  - {col[1]}: {col[2]} (not null: {col[3]}, default: {col[4]})")
        
        # Get sample data
        cursor.execute("SELECT id, project_id, version_number, content_type FROM paper_version LIMIT 5")
        sample_data = cursor.fetchall()
        logger.info(f"Sample data (up to 5 rows): {sample_data}")
        
        # Using SQLAlchemy inspector
        engine = create_engine(f'sqlite:///{db_path}')
        inspector = inspect(engine)
        
        logger.info("SQLAlchemy inspector results for paper_version:")
        for col in inspector.get_columns('paper_version'):
            logger.info(f"  - {col['name']}: {col['type']}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error inspecting database: {str(e)}")
        if 'conn' in locals():
            conn.close()

def inspect_with_sqlalchemy():
    """Inspect database using SQLAlchemy"""
    try:
        # Create engine using the same connection string as the app
        engine = create_engine('sqlite:///instance/paper_projects.db')
        
        # Get SQLAlchemy inspector
        inspector = inspect(engine)
        
        # Get columns for paper_version table
        columns = inspector.get_columns('paper_version')
        logger.info("SQLAlchemy inspector results for paper_version:")
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")
        
        # Compare with model definition
        model_columns = [column.key for column in PaperVersion.__table__.columns]
        logger.info(f"Columns in PaperVersion model: {model_columns}")
        
        # Check for discrepancies
        db_columns = [col['name'] for col in columns]
        missing_in_db = [col for col in model_columns if col not in db_columns]
        missing_in_model = [col for col in db_columns if col not in model_columns]
        
        if missing_in_db:
            logger.warning(f"Columns in model but not in database: {missing_in_db}")
        if missing_in_model:
            logger.warning(f"Columns in database but not in model: {missing_in_model}")
    except Exception as e:
        logger.error(f"Error inspecting with SQLAlchemy: {str(e)}")

if __name__ == "__main__":
    inspect_database()
    inspect_with_sqlalchemy() 