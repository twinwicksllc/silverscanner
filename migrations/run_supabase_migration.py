"""
Direct Supabase Migration Script
Connects to Supabase PostgreSQL directly using connection string
"""

import os
from sqlalchemy import create_engine, text

def run_migration_on_supabase():
    """Execute migration directly on Supabase"""
    
    print("\n" + "="*60)
    print("SUPABASE DATABASE MIGRATION")
    print("="*60 + "\n")
    
    # Read the SQL migration file
    migration_path = '/workspace/silver_scanner/migrations/add_time_listed_column.sql'
    with open(migration_path, 'r') as f:
        sql_content = f.read()
    
    print(f"Migration file: {migration_path}")
    print(f"SQL content:\n{sql_content}\n")
    
    # Get DATABASE_URL from environment
    # You'll need to set this in the environment or paste it directly
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("\nPlease set the DATABASE_URL environment variable:")
        print("export DATABASE_URL='postgresql://postgres:YOUR_PASSWORD@db.XXXX.supabase.co:5432/postgres'")
        print("\nOr modify this script and paste the URL directly.")
        return False
    
    print(f"Connecting to Supabase...")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Connect and execute
        with engine.connect() as conn:
            print("✅ Connected to database")
            
            # Split SQL by semicolon and execute each statement
            # Remove comments and empty lines
            statements = []
            for line in sql_content.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    statements.append(line)
            
            # Reconstruct statements
            full_sql = ' '.join(statements)
            
            # Split by semicolon for individual statements
            individual_statements = [s.strip() + ';' for s in full_sql.split(';') if s.strip()]
            
            print(f"\nExecuting {len(individual_statements)} SQL statements...\n")
            
            for i, stmt in enumerate(individual_statements, 1):
                try:
                    print(f"Statement {i}/{len(individual_statements)}: {stmt[:80]}...")
                    result = conn.execute(text(stmt))
                    conn.commit()
                    print(f"   ✅ Success")
                except Exception as e:
                    # Check if it's a "already exists" error (which is OK)
                    if "already exists" in str(e) or "duplicate column" in str(e).lower():
                        print(f"   ⚠️  Already exists (skipping)")
                        conn.commit()
                    else:
                        print(f"   ❌ Error: {e}")
                        raise
            
            print("\n" + "="*60)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nThe 'time_listed' column has been added to the deals table.")
            print("New deals will now include listing start time information.")
            
            return True
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    import sys
    success = run_migration_on_supabase()
    sys.exit(0 if success else 1)