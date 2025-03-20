import os
import sys
import logging
import sqlite3
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join('instance', 'academic_agent.db')

def fix_database():
    """Update database tables with correct constraints and fix auto-increment issues."""
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return False
        
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enable foreign keys to check current status
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        logger.info(f"Foreign keys status before: {result[0]}")
        
        # Disable foreign keys during migration
        cursor.execute("PRAGMA foreign_keys = OFF")
        logger.info("Foreign keys disabled for migration")
        
        # Check if leftover temporary tables exist from a previous failed run and drop them
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_message_new'")
        if cursor.fetchone():
            logger.info("Found existing agent_message_new table, dropping it...")
            cursor.execute("DROP TABLE agent_message_new")
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paper_version_new'")
        if cursor.fetchone():
            logger.info("Found existing paper_version_new table, dropping it...")
            cursor.execute("DROP TABLE paper_version_new")
            
        # STEP 1: Fix the paper_version table first
        logger.info("Checking paper_version table for auto-increment issues...")
        
        # Check if paper_version table has AUTOINCREMENT for id column
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='paper_version'")
        table_def = cursor.fetchone()[0]
        logger.info(f"Current paper_version table definition: {table_def}")
        
        # Fix paper_version table if it doesn't have proper AUTOINCREMENT
        if "AUTOINCREMENT" not in table_def:
            logger.info("Fixing paper_version table with proper AUTOINCREMENT...")
            
            # Get current schema structure
            cursor.execute("PRAGMA table_info(paper_version)")
            columns = cursor.fetchall()
            logger.info(f"Paper version table columns: {columns}")
            
            # Build column definitions
            column_defs = []
            for col in columns:
                name = col[1]
                type_name = col[2]
                not_null = "NOT NULL" if col[3] == 1 else ""
                if name == "id":
                    column_defs.append(f"id INTEGER PRIMARY KEY AUTOINCREMENT")
                else:
                    column_defs.append(f"{name} {type_name} {not_null}")
            
            # Create the new table with proper AUTOINCREMENT
            create_stmt = f'''
            CREATE TABLE paper_version_new (
                {", ".join(column_defs)},
                FOREIGN KEY (project_id) REFERENCES paper_project(id) ON DELETE CASCADE
            )
            '''
            logger.info(f"Creating paper_version_new with: {create_stmt}")
            cursor.execute(create_stmt)
            
            # Copy data, but don't copy the id column
            cursor.execute("SELECT project_id, version_number, content_type, content, created_at FROM paper_version")
            rows = cursor.fetchall()
            
            if rows:
                logger.info(f"Copying {len(rows)} rows to paper_version_new...")
                for row in rows:
                    cursor.execute(
                        "INSERT INTO paper_version_new (project_id, version_number, content_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
                        row
                    )
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE paper_version")
            cursor.execute("ALTER TABLE paper_version_new RENAME TO paper_version")
            logger.info("paper_version table updated successfully with AUTOINCREMENT")
        
        # STEP 2: Now fix the agent_message table for CASCADE delete
        cursor.execute("PRAGMA foreign_key_list(agent_message)")
        fk_check = cursor.fetchall()
        logger.info(f"Current foreign key constraints: {fk_check}")
        
        if not fk_check or 'CASCADE' not in str(fk_check):
            logger.info("Updating agent_message table with CASCADE delete...")
            
            # Check current schema of agent_message table
            cursor.execute("PRAGMA table_info(agent_message)")
            columns = cursor.fetchall()
            logger.info(f"Agent message table columns: {columns}")
            
            # Check if sender/receiver or agent_type column exists by checking column names
            column_names = [col[1] for col in columns]
            logger.info(f"Column names: {column_names}")
            
            # Create appropriate new table schema based on existing columns
            if 'agent_type' in column_names:
                # Use the old schema with agent_type
                cursor.execute('''
                CREATE TABLE agent_message_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    project_id INTEGER NOT NULL,
                    agent_type VARCHAR(50),
                    message_type VARCHAR(50),
                    message TEXT,
                    created_at DATETIME,
                    FOREIGN KEY (project_id) REFERENCES paper_project(id) ON DELETE CASCADE
                )
                ''')
            elif 'sender' in column_names and 'receiver' in column_names:
                # Use the new schema with sender/receiver
                cursor.execute('''
                CREATE TABLE agent_message_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    project_id INTEGER NOT NULL,
                    sender VARCHAR(50) NOT NULL,
                    receiver VARCHAR(50),
                    content TEXT NOT NULL,
                    message_type VARCHAR(50),
                    created_at DATETIME,
                    FOREIGN KEY (project_id) REFERENCES paper_project(id) ON DELETE CASCADE
                )
                ''')
            else:
                logger.error("Unknown agent_message table schema - cannot update")
                conn.close()
                return False
            
            # Copy data from old table to new table
            try:
                # Don't copy the id field
                if 'agent_type' in column_names:
                    cursor.execute("SELECT project_id, agent_type, message_type, message, created_at FROM agent_message")
                    rows = cursor.fetchall()
                    for row in rows:
                        cursor.execute(
                            "INSERT INTO agent_message_new (project_id, agent_type, message_type, message, created_at) VALUES (?, ?, ?, ?, ?)",
                            row
                        )
                elif 'sender' in column_names and 'receiver' in column_names:
                    cursor.execute("SELECT project_id, sender, receiver, content, message_type, created_at FROM agent_message")
                    rows = cursor.fetchall()
                    for row in rows:
                        cursor.execute(
                            "INSERT INTO agent_message_new (project_id, sender, receiver, content, message_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            row
                        )
                
                logger.info("Data copied successfully to agent_message_new")
            except sqlite3.Error as e:
                logger.error(f"Error copying data: {str(e)}")
                # Get table definitions for debugging
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_message'")
                old_def = cursor.fetchone()
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_message_new'")
                new_def = cursor.fetchone()
                logger.info(f"Old table definition: {old_def}")
                logger.info(f"New table definition: {new_def}")
                conn.close()
                return False
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE agent_message")
            cursor.execute("ALTER TABLE agent_message_new RENAME TO agent_message")
            logger.info("agent_message table updated successfully")
        else:
            logger.info("Foreign key constraints already have CASCADE delete - no changes needed")
        
        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verify foreign keys are enabled and constraints updated
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        logger.info(f"Foreign keys status after: {result[0]}")
        
        cursor.execute("PRAGMA foreign_key_list(agent_message)")
        fk_check = cursor.fetchall()
        logger.info(f"Updated foreign key constraints: {fk_check}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting database fix script")
    success = fix_database()
    if success:
        logger.info("Database fix completed successfully")
    else:
        logger.error("Database fix failed") 