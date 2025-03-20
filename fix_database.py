import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    # Get the database path
    db_path = os.path.join('instance', 'academic_agent.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if content_type column exists
        cursor.execute("PRAGMA table_info(paper_version)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'content_type' not in columns:
            logger.info("Adding content_type column to paper_version table...")
            # Add the content_type column with default value 'research'
            cursor.execute("""
                ALTER TABLE paper_version 
                ADD COLUMN content_type TEXT DEFAULT 'research'
            """)
            conn.commit()
            logger.info("content_type column added successfully")
        else:
            logger.info("content_type column already exists")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error fixing database: {str(e)}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_database() 