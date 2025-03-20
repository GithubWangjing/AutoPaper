import os
import sqlite3
import logging
from flask import Flask
from models import db, PaperVersion, PaperProject

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_direct_sqlite_query():
    """Test querying the database directly with SQLite"""
    try:
        db_path = "instance/paper_projects.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try to query using content_type (this should succeed if the column exists)
        logger.info("Testing direct SQLite query with content_type column...")
        cursor.execute("""
            SELECT id, project_id, version_number, content_type
            FROM paper_version
            LIMIT 5
        """)
        rows = cursor.fetchall()
        logger.info(f"Query result: {rows}")
        
        # Create a sample record if none exists
        if not rows:
            logger.info("No records found, creating a test record...")
            cursor.execute("""
                INSERT INTO paper_version 
                (project_id, version_number, content_type, content, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (1, 1, 'research', 'Test content', ))
            conn.commit()
            logger.info("Test record created successfully")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error in direct SQLite query: {str(e)}")

def test_sqlalchemy_query():
    """Test querying the database using SQLAlchemy"""
    try:
        # Create a minimal Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/paper_projects.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            logger.info("Testing SQLAlchemy query with content_type column...")
            # Try to query using content_type
            versions = PaperVersion.query.filter_by(content_type='research').limit(5).all()
            logger.info(f"Found {len(versions)} versions with content_type='research'")
            
            for version in versions:
                logger.info(f"Version ID: {version.id}, Project ID: {version.project_id}, "
                            f"Version #: {version.version_number}, Content type: {version.content_type}")
    except Exception as e:
        logger.error(f"Error in SQLAlchemy query: {str(e)}")

def recreate_content_type_column():
    """Recreate the content_type column in the database"""
    try:
        db_path = "instance/paper_projects.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if content_type column exists
        cursor.execute("PRAGMA table_info(paper_version)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'content_type' in columns:
            logger.info("Dropping content_type column (requires SQLite rebuild)...")
            # SQLite doesn't support DROP COLUMN directly, so we need to rebuild the table
            
            # 1. Create a new table without the column
            cursor.execute("""
                CREATE TABLE paper_version_new (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    created_by VARCHAR(50),
                    version_type VARCHAR(50),
                    created_at DATETIME,
                    FOREIGN KEY(project_id) REFERENCES paper_project(id)
                )
            """)
            
            # 2. Copy data to the new table
            cursor.execute("""
                INSERT INTO paper_version_new 
                SELECT id, project_id, content, version_number, created_by, version_type, created_at
                FROM paper_version
            """)
            
            # 3. Drop the old table
            cursor.execute("DROP TABLE paper_version")
            
            # 4. Rename the new table to the original name
            cursor.execute("ALTER TABLE paper_version_new RENAME TO paper_version")
            
            logger.info("Table rebuilt without content_type column")
        
        # Add the content_type column (fresh)
        logger.info("Adding content_type column...")
        cursor.execute("ALTER TABLE paper_version ADD COLUMN content_type TEXT DEFAULT 'research'")
        
        # Update existing records
        cursor.execute("""
            UPDATE paper_version 
            SET content_type = 
                CASE 
                    WHEN version_number = 1 THEN 'research'
                    WHEN version_number = 2 THEN 'draft'
                    WHEN version_number = 3 THEN 'review'
                    WHEN version_number = 4 THEN 'final'
                    ELSE 'research'
                END
        """)
        
        conn.commit()
        logger.info("content_type column recreated successfully")
        conn.close()
    except Exception as e:
        logger.error(f"Error recreating content_type column: {str(e)}")

if __name__ == "__main__":
    # Uncomment the line below to force recreation of the content_type column
    recreate_content_type_column()
    
    # Test querying the database
    test_direct_sqlite_query()
    test_sqlalchemy_query() 