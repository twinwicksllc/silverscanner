"""
Direct database migration script for Supabase
This script connects to Supabase and adds the time_listed column
"""

import os
import sys
from sqlalchemy import create_engine, text

def run_migration():
    """Add time_listed column to deals table"""
    
    print("="*60)
    print("DATABASE MIGRATION: Add time_listed column")
    print("="*60)
    print()
    
    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print()
        print("Please set it like this:")
        print("export DATABASE_URL='postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres'")
        print()
        print("Or run this script on Render where DATABASE_URL is already set.")
        return False
    
    print(f"✅ Database URL found (ending with ...{database_url[-20:]})")
    print()
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("✅ Connected to database")
            print()
            
            # Check if column already exists
            print("🔍 Checking if time_listed column exists...")
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'deals' 
            AND column_name = 'time_listed';
            """
            
            result = conn.execute(text(check_sql))
            existing = result.fetchone()
            
            if existing:
                print("✅ Column time_listed already exists!")
                print()
                print("="*60)
                print("Migration Result: SKIPPED (already exists)")
                print("="*60)
                return True
            
            print("   Column does not exist - will add it")
            print()
            
            # Add the column
            print("🔧 Adding time_listed column to deals table...")
            alter_sql = """
            ALTER TABLE deals 
            ADD COLUMN time_listed TIMESTAMP;
            """
            
            conn.execute(text(alter_sql))
            conn.commit()
            print("   ✅ Column added successfully")
            print()
            
            # Create index
            print("🔧 Creating index on time_listed column...")
            index_sql = """
            CREATE INDEX idx_deals_time_listed 
            ON deals(time_listed);
            """
            
            try:
                conn.execute(text(index_sql))
                conn.commit()
                print("   ✅ Index created successfully")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Index already exists (skipping)")
                else:
                    raise
            
            print()
            print("="*60)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*60)
            print()
            print("The 'time_listed' column has been added to the deals table.")
            print("New deals will now include listing start time information.")
            print()
            
            return True
            
    except Exception as e:
        print()
        print("❌ MIGRATION FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)