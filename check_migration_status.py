#!/usr/bin/env python3
"""
Check if the price_history metal_type migration has been applied
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from database.models import DatabaseManager

def check_migration():
    """Check migration status"""
    
    print("=" * 60)
    print("MIGRATION STATUS CHECK")
    print("=" * 60)
    
    try:
        db = DatabaseManager()
        session = db.get_session()
        
        # Check price_history table schema
        print("\n[price_history table schema]")
        result = session.execute("PRAGMA table_info(price_history)")
        columns = result.fetchall()
        
        has_metal_type = False
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
            if col[1] == 'metal_type':
                has_metal_type = True
        
        # Check indexes
        print("\n[Indexes on price_history]")
        result = session.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='price_history'")
        indexes = result.fetchall()
        for idx in indexes:
            print(f"  • {idx[0]}")
        
        # Check data distribution
        print("\n[Price history data distribution]")
        if has_metal_type:
            result = session.execute("SELECT metal_type, COUNT(*) as count FROM price_history GROUP BY metal_type")
            rows = result.fetchall()
            if rows:
                for row in rows:
                    print(f"  • {row[0]}: {row[1]} records")
            else:
                print("  No price history records found")
        else:
            result = session.execute("SELECT COUNT(*) as count FROM price_history")
            count = result.fetchone()[0]
            print(f"  Total records: {count} (metal_type column missing)")
        
        session.close()
        
        # Summary
        print("\n" + "=" * 60)
        if has_metal_type:
            print("✅ MIGRATION APPLIED")
            print("=" * 60)
            print("\nThe metal_type column exists in the price_history table.")
            print("Gold price history should now be tracked properly.")
        else:
            print("❌ MIGRATION NOT APPLIED")
            print("=" * 60)
            print("\nThe metal_type column is missing from the price_history table.")
            print("Please run the migration script:")
            print("  python manual_price_history_migration.py")
        
        return has_metal_type
        
    except Exception as e:
        print(f"\nError checking migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_migration()