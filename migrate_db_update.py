import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add custom model columns to the PaperProject table if they don't exist."""
    # Get database URI from environment or use default
    db_uri = os.environ.get("DATABASE_URI", 'sqlite:///instance/paper_projects.db')
    
    # Extract the path for SQLite databases
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri[10:]
    else:
        print(f"Unsupported database URI format: {db_uri}")
        return
    
    print(f"Migrating database at: {db_path}")
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get the column names from the paper_project table
    cursor.execute("PRAGMA table_info(paper_project)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # Add each custom model column if it doesn't exist
    columns_to_add = [
        ("custom_model_endpoint", "VARCHAR(255)"),
        ("custom_model_api_key", "VARCHAR(255)"),
        ("custom_model_name", "VARCHAR(100)"),
        ("custom_model_temperature", "FLOAT DEFAULT 0.7"),
        ("custom_model_max_tokens", "INTEGER DEFAULT 2000")
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE paper_project ADD COLUMN {column_name} {column_type}")
                print(f"Added column: {column_name}")
            except sqlite3.Error as e:
                print(f"Error adding column {column_name}: {e}")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database migration completed.")

if __name__ == "__main__":
    migrate_database() 