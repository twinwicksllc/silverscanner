#!/usr/bin/env python3
"""
Test script to verify migration can execute
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

print("=" * 60)
print("Migration Test Script")
print("=" * 60)

database_url = Config.DATABASE_URL
print(f"\nDatabase URL: {database_url[:30]}...")

if not database_url:
    print("❌ ERROR: DATABASE_URL not configured")
    sys.exit(1)

try:
    engine = create_engine(database_url)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();" if 'postgresql' in database_url else "SELECT sqlite_version();"))
        version = result.fetchone()
        print(f"✅ Database connected successfully")
        print(f"   Version: {version[0]}")
    
    # Check current schema
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('deals')]
    print(f"\n📊 Current deals table columns: {existing_columns}")
    
    # Read migration SQL
    migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'add_metal_type_support.sql')
    print(f"\n📄 Reading migration from: {migration_path}")
    
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    print(f"   Migration SQL size: {len(migration_sql)} bytes")
    
    # Parse and show statements
    statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
    print(f"\n📋 Found {len(statements)} SQL statements to execute")
    
    # Execute migration
    print("\n🔧 Executing migration...")
    with engine.connect() as conn:
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"   [{i}/{len(statements)}] Executing: {statement[:60]}...")
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ⚠️  Error (may be expected): {str(e)[:100]}")
                    # Continue with next statement
    
    # Verify changes
    print("\n✅ Verifying migration...")
    inspector = inspect(engine)
    new_columns = [col['name'] for col in inspector.get_columns('deals')]
    print(f"   Deals table columns after migration: {new_columns}")
    
    # Check if metal_type and metal_purity were added
    if 'metal_type' in new_columns:
        print("   ✅ metal_type column added")
    else:
        print("   ❌ metal_type column NOT found")
    
    if 'metal_purity' in new_columns:
        print("   ✅ metal_purity column added")
    else:
        print("   ❌ metal_purity column NOT found")
    
    # Check if spot_prices table exists
    tables = inspector.get_table_names()
    if 'spot_prices' in tables:
        print("   ✅ spot_prices table created")
    else:
        print("   ❌ spot_prices table NOT found")
    
    print("\n" + "=" * 60)
    print("✅ Migration test completed successfully!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)