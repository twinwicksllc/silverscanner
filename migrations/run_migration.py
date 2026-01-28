"""
Database Migration Script
Executes SQL migrations against the Supabase PostgreSQL database
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment or use SQLite fallback"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        print(f"Using PostgreSQL database (Supabase)")
        return database_url
    else:
        print(f"Using SQLite database (fallback)")
        db_path = os.path.join(Path(__file__).parent.parent, 'silver_scanner.db')
        return f'sqlite:///{db_path}'

def run_migration(migration_file):
    """Execute a SQL migration file"""
    
    # Read migration SQL
    migration_path = Path(__file__).parent / migration_file
    if not migration_path.exists():
        print(f"Error: Migration file not found: {migration_path}")
        return False
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    print(f"\n{'='*60}")
    print(f"Migration: {migration_file}")
    print(f"{'='*60}\n")
    print(f"SQL to execute:\n{migration_sql}\n")
    
    # Connect to database
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            # Execute migration
            print("Executing migration...")
            result = conn.execute(text(migration_sql))
            
            # Commit transaction
            trans.commit()
            
            print(f"✅ Migration completed successfully!")
            print(f"   Rows affected: {result.rowcount if hasattr(result, 'rowcount') else 'N/A'}")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    
    finally:
        engine.dispose()

def create_migration_history_table():
    """Create migration history table if it doesn't exist"""
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    sql = """
    CREATE TABLE IF NOT EXISTS migration_history (
        id SERIAL PRIMARY KEY,
        migration_name VARCHAR(255) UNIQUE NOT NULL,
        applied_at TIMESTAMP DEFAULT NOW(),
        status VARCHAR(50) DEFAULT 'completed'
    );
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("✅ Migration history table ready")
    except Exception as e:
        print(f"Warning: Could not create migration history table: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DATABASE MIGRATION TOOL")
    print("="*60)
    
    # Ensure migration history table exists
    create_migration_history_table()
    
    # Run the specific migration
    success = run_migration('add_time_listed_column.sql')
    
    if success:
        print("\n✅ All migrations completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)