import os
import sqlite3
import logging
from flask import Flask
from models import db, PaperProject

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/paper_projects.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def check_existing_database():
    """Check if the database file exists and return its path"""
    instance_dir = os.path.join(os.getcwd(), 'instance')
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        logger.info(f"Created instance directory at {instance_dir}")
    
    db_path = os.path.join(instance_dir, 'paper_projects.db')
    exists = os.path.exists(db_path)
    logger.info(f"Database file exists: {exists}")
    return db_path, exists

def add_research_source_column(db_path):
    """Add research_source column to the PaperProject table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(paper_project)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'research_source' not in columns:
            logger.info("Adding research_source column to paper_project table...")
            cursor.execute("ALTER TABLE paper_project ADD COLUMN research_source TEXT DEFAULT 'none'")
            conn.commit()
            logger.info("Column added successfully")
        else:
            logger.info("research_source column already exists")
            
        # Check if the model_type column exists
        if 'model_type' not in columns:
            logger.info("Adding model_type column to paper_project table...")
            cursor.execute("ALTER TABLE paper_project ADD COLUMN model_type TEXT DEFAULT 'siliconflow'")
            conn.commit()
            logger.info("Column added successfully")
        else:
            logger.info("model_type column already exists")
            
        # Update existing projects with a model_type where it's null
        cursor.execute("UPDATE paper_project SET model_type = 'siliconflow' WHERE model_type IS NULL")
        
        # Update projects with research_source based on model_type for backward compatibility
        cursor.execute("""
            UPDATE paper_project 
            SET research_source = 
                CASE 
                    WHEN model_type = 'mcp' THEN 'google_scholar' 
                    WHEN model_type = 'arxiv' THEN 'arxiv'
                    ELSE 'none'
                END,
                model_type = 
                CASE 
                    WHEN model_type = 'mcp' THEN 'siliconflow'
                    WHEN model_type = 'arxiv' THEN 'siliconflow'
                    ELSE model_type
                END
            WHERE research_source = 'none'
        """)
        
        conn.commit()
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error migrating database: {str(e)}")
    finally:
        if conn:
            conn.close()

def add_content_type_column(db_path):
    """Add content_type column to the PaperVersion table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the paper_version table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='paper_version'
        """)
        table_exists = cursor.fetchone()
        
        if not table_exists:
            logger.warning("paper_version table does not exist - skipping migration")
            return
            
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(paper_version)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'content_type' not in columns:
            logger.info("Adding content_type column to paper_version table...")
            cursor.execute("ALTER TABLE paper_version ADD COLUMN content_type TEXT DEFAULT 'research'")
            conn.commit()
            logger.info("Column added successfully")
            
            # Update existing versions with appropriate content_type based on version_number
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
            logger.info("Updated existing records with appropriate content_type values")
        else:
            logger.info("content_type column already exists in paper_version table")
            
        conn.commit()
        logger.info("PaperVersion migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error migrating paper_version table: {str(e)}")
    finally:
        if conn:
            conn.close()

def migrate_database():
    """迁移数据库结构"""
    try:
        print("开始数据库迁移...")
        
        # 连接数据库
        conn = sqlite3.connect('instance/paper_projects.db')
        cursor = conn.cursor()
        
        # 检查表是否存在
        tables = []
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for row in cursor.fetchall():
            tables.append(row[0])
        
        print(f"现有数据库表: {tables}")
        
        # 检查并更新paper_project表
        if 'paper_project' in tables:
            # 获取已有列信息
            columns = []
            cursor.execute(f"PRAGMA table_info(paper_project)")
            for column_info in cursor.fetchall():
                columns.append(column_info[1])  # column name is at index 1
            
            print(f"paper_project表现有列: {columns}")
            
            # 添加模型自定义字段
            if 'custom_model_endpoint' not in columns:
                print("添加custom_model_endpoint列...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN custom_model_endpoint TEXT;")
                
            if 'custom_model_api_key' not in columns:
                print("添加custom_model_api_key列...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN custom_model_api_key TEXT;")
                
            if 'custom_model_name' not in columns:
                print("添加custom_model_name列...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN custom_model_name TEXT;")
                
            if 'custom_model_temperature' not in columns:
                print("添加custom_model_temperature列...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN custom_model_temperature REAL;")
                
            if 'custom_model_max_tokens' not in columns:
                print("添加custom_model_max_tokens列...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN custom_model_max_tokens INTEGER;")
            
            # Check if the model_type column exists
            if 'model_type' not in columns:
                print("Adding model_type column to paper_project table...")
                cursor.execute("ALTER TABLE paper_project ADD COLUMN model_type TEXT DEFAULT 'siliconflow'")
                conn.commit()
                print("Column added successfully")
            else:
                print("model_type column already exists")
            
            # Update existing projects with a model_type where it's null
            cursor.execute("UPDATE paper_project SET model_type = 'siliconflow' WHERE model_type IS NULL")
            
            # Update projects with research_source based on model_type for backward compatibility
            cursor.execute("""
                UPDATE paper_project 
                SET research_source = 
                    CASE 
                        WHEN model_type = 'mcp' THEN 'google_scholar' 
                        WHEN model_type = 'arxiv' THEN 'arxiv'
                        ELSE 'none'
                    END,
                    model_type = 
                    CASE 
                        WHEN model_type = 'mcp' THEN 'siliconflow'
                        WHEN model_type = 'arxiv' THEN 'siliconflow'
                        ELSE model_type
                    END
                WHERE research_source = 'none'
            """)
            
            conn.commit()
            print("Migration completed successfully")
            
        # Check if the paper_version table exists
        if 'paper_version' not in tables:
            print("paper_version table does not exist - skipping migration")
            return
            
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(paper_version)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'content_type' not in columns:
            print("Adding content_type column to paper_version table...")
            cursor.execute("ALTER TABLE paper_version ADD COLUMN content_type TEXT DEFAULT 'research'")
            conn.commit()
            print("Column added successfully")
            
            # Update existing versions with appropriate content_type based on version_number
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
            print("Updated existing records with appropriate content_type values")
        else:
            print("content_type column already exists in paper_version table")
            
        conn.commit()
        print("PaperVersion migration completed successfully")
        
    except Exception as e:
        print(f"Error migrating database: {str(e)}")
    finally:
        if conn:
            conn.close()

def main():
    logger.info("Starting database migration...")
    db_path, exists = check_existing_database()
    
    if exists:
        migrate_database()
    else:
        logger.info("No existing database found. Creating new database...")
        
    # 提示完成
    logger.info("Migration complete")
    print("数据库迁移完成!")
    print("你现在可以启动应用: python app.py")
    
if __name__ == "__main__":
    main() 