#!/usr/bin/env python3
"""
Manual migration script to add metal_type column to price_history table
This can be run directly on Render's shell if the API endpoint fails
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from database.models import DatabaseManager

def migrate_price_history():
    """Add metal_type column to price_history table"""
    
    print("=" * 60)
    print("PRICE HISTORY METAL_TYPE MIGRATION")
    print("=" * 60)
    
    try:
        db = DatabaseManager()
        session = db.get_session()
        
        print("\n[Step 1] Adding metal_type column to price_history...")
        try:
            session.execute("ALTER TABLE price_history ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'")
            session.commit()
            print("✓ Successfully added metal_type column")
        except Exception as e:
            session.rollback()
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("✓ metal_type column already exists (skipping)")
            else:
                print(f"✗ Error adding column: {e}")
                raise
        
        print("\n[Step 2] Creating index on metal_type...")
        try:
            session.execute("CREATE INDEX IF NOT EXISTS idx_price_history_metal_type ON price_history(metal_type)")
            session.commit()
            print("✓ Successfully created index on metal_type")
        except Exception as e:
            session.rollback()
            if 'already exists' in str(e).lower():
                print("✓ Index already exists (skipping)")
            else:
                print(f"✗ Error creating index: {e}")
                raise
        
        print("\n[Step 3] Updating existing records...")
        try:
            result = session.execute("UPDATE price_history SET metal_type = 'silver' WHERE metal_type IS NULL OR metal_type = ''")
            session.commit()
            print(f"✓ Updated {result.rowcount} existing records")
        except Exception as e:
            session.rollback()
            print(f"✗ Error updating records: {e}")
            raise
        
        print("\n[Step 4] Creating composite index (metal_type, timestamp)...")
        try:
            session.execute("CREATE INDEX IF NOT EXISTS idx_price_history_metal_timestamp ON price_history(metal_type, timestamp)")
            session.commit()
            print("✓ Successfully created composite index")
        except Exception as e:
            session.rollback()
            if 'already exists' in str(e).lower():
                print("✓ Composite index already exists (skipping)")
            else:
                print(f"✗ Error creating composite index: {e}")
                raise
        
        session.close()
        
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nChanges made:")
        print("  • Added metal_type column to price_history table")
        print("  • Created index: idx_price_history_metal_type")
        print("  • Created index: idx_price_history_metal_timestamp")
        print("  • Updated existing records with metal_type='silver'")
        print("\nThe price history will now track prices for multiple metals.")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED!")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_price_history()
    sys.exit(0 if success else 1)