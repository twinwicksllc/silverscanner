#!/usr/bin/env python3
"""
Run multi-metal support migration
Compatible with both PostgreSQL and SQLite
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def main():
    """Main migration function"""
    
    print("=" * 60)
    print("Multi-Metal Support Migration")
    print("=" * 60)

    database_url = Config.DATABASE_URL
    print(f"\nDatabase URL: {database_url[:50]}...")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not configured")
        sys.exit(1)

    try:
        engine = create_engine(database_url)
        is_postgres = 'postgresql' in database_url
        
        print(f"Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        # Test connection
        with engine.connect() as conn:
            if is_postgres:
                result = conn.execute(text("SELECT version();"))
            else:
                result = conn.execute(text("SELECT sqlite_version();"))
            version = result.fetchone()
            print(f"✅ Database connected (version: {version[0][:50]}...)")
        
        # Check current schema
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('deals')]
        print(f"\n📊 Current deals table has {len(existing_columns)} columns")
        
        # Migration steps
        print("\n🔧 Starting migration...")
        
        with engine.connect() as conn:
            # Step 1: Add metal_type column
            if 'metal_type' not in existing_columns:
                print("   [1/7] Adding metal_type column...")
                conn.execute(text("ALTER TABLE deals ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'"))
                conn.commit()
                print("   ✅ metal_type column added")
            else:
                print("   [1/7] metal_type column already exists - skipping")
            
            # Step 2: Add metal_purity column
            if 'metal_purity' not in existing_columns:
                print("   [2/7] Adding metal_purity column...")
                conn.execute(text("ALTER TABLE deals ADD COLUMN metal_purity FLOAT DEFAULT 1.0"))
                conn.commit()
                print("   ✅ metal_purity column added")
            else:
                print("   [2/7] metal_purity column already exists - skipping")
            
            # Step 3: Rename silver_weight_oz to metal_weight_oz (PostgreSQL only)
            if is_postgres:
                inspector = inspect(engine)
                columns = [col['name'] for col in inspector.get_columns('deals')]
                if 'silver_weight_oz' in columns and 'metal_weight_oz' not in columns:
                    print("   [3/7] Renaming silver_weight_oz to metal_weight_oz...")
                    conn.execute(text("ALTER TABLE deals RENAME COLUMN silver_weight_oz TO metal_weight_oz"))
                    conn.commit()
                    print("   ✅ Column renamed")
                else:
                    print("   [3/7] Column rename not needed - skipping")
            else:
                # SQLite: create new table and copy data
                inspector = inspect(engine)
                columns = [col['name'] for col in inspector.get_columns('deals')]
                if 'silver_weight_oz' in columns and 'metal_weight_oz' not in columns:
                    print("   [3/7] Renaming silver_weight_oz to metal_weight_oz (SQLite)...")
                    # Get all columns except silver_weight_oz
                    cols = [c for c in columns if c != 'silver_weight_oz'] + ['metal_weight_oz']
                    cols_str = ', '.join(cols)
                    
                    # Create temp table
                    conn.execute(text("""
                        CREATE TABLE deals_new AS
                        SELECT id, item_id, title, price, shipping_cost, total_cost, coin_type, coin_name,
                               silver_weight_oz AS metal_weight_oz, quantity, face_value, spot_price,
                               cost_per_oz, discount_percent, savings_per_oz, threshold, seller_username,
                               seller_feedback, condition, item_url, image_url, time_listed, scan_id,
                               qualified_at, confidence, is_valid, is_hidden, hidden_at, metal_type, metal_purity
                        FROM deals
                    """))
                    conn.commit()
                    
                    # Drop old table and rename new one
                    conn.execute(text("DROP TABLE deals"))
                    conn.commit()
                    conn.execute(text("ALTER TABLE deals_new RENAME TO deals"))
                    conn.commit()
                    print("   ✅ Column renamed")
                else:
                    print("   [3/7] Column rename not needed - skipping")
            
            # Step 4: Create index on metal_type
            print("   [4/7] Creating index on metal_type...")
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_deals_metal_type ON deals(metal_type)"))
                conn.commit()
                print("   ✅ Index created")
            except Exception as e:
                print(f"   ⚠️  Index creation skipped (may already exist): {str(e)[:50]}")
            
            # Step 5: Create spot_prices table
            tables = inspector.get_table_names()
            if 'spot_prices' not in tables:
                print("   [5/7] Creating spot_prices table...")
                if is_postgres:
                    conn.execute(text("""
                        CREATE TABLE spot_prices (
                            id SERIAL PRIMARY KEY,
                            metal_type VARCHAR(20) NOT NULL,
                            price FLOAT NOT NULL,
                            source VARCHAR(100),
                            timestamp TIMESTAMP DEFAULT NOW(),
                            verified BOOLEAN DEFAULT FALSE
                        )
                    """))
                else:
                    conn.execute(text("""
                        CREATE TABLE spot_prices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            metal_type VARCHAR(20) NOT NULL,
                            price FLOAT NOT NULL,
                            source VARCHAR(100),
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            verified BOOLEAN DEFAULT 0
                        )
                    """))
                conn.commit()
                print("   ✅ spot_prices table created")
            else:
                print("   [5/7] spot_prices table already exists - skipping")
            
            # Step 6: Create index on spot_prices
            print("   [6/7] Creating index on spot_prices...")
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_spot_prices_metal_timestamp ON spot_prices(metal_type, timestamp DESC)"))
                conn.commit()
                print("   ✅ Index created")
            except Exception as e:
                print(f"   ⚠️  Index creation skipped: {str(e)[:50]}")
            
            # Step 7: Update price_history table
            inspector = inspect(engine)
            price_history_columns = [col['name'] for col in inspector.get_columns('price_history')]
            if 'metal_type' not in price_history_columns:
                print("   [7/7] Adding metal_type to price_history...")
                conn.execute(text("ALTER TABLE price_history ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'"))
                conn.commit()
                print("   ✅ Column added")
            else:
                print("   [7/7] price_history already has metal_type - skipping")
            
            # Create index on price_history
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_price_history_metal ON price_history(metal_type, timestamp DESC)"))
                conn.commit()
                print("   ✅ Index created on price_history")
            except Exception as e:
                print(f"   ⚠️  Index creation skipped: {str(e)[:50]}")
        
        # Verify changes
        print("\n✅ Verifying migration...")
        inspector = inspect(engine)
        new_columns = [col['name'] for col in inspector.get_columns('deals')]
        tables = inspector.get_table_names()
        
        print(f"\n📊 Results:")
        if 'metal_type' in new_columns:
            print("   ✅ metal_type column in deals table")
        else:
            print("   ❌ metal_type column NOT found")
        
        if 'metal_purity' in new_columns:
            print("   ✅ metal_purity column in deals table")
        else:
            print("   ❌ metal_purity column NOT found")
        
        if 'metal_weight_oz' in new_columns or 'silver_weight_oz' in new_columns:
            weight_col = 'metal_weight_oz' if 'metal_weight_oz' in new_columns else 'silver_weight_oz'
            print(f"   ✅ {weight_col} column present")
        else:
            print("   ❌ Weight column NOT found")
        
        if 'spot_prices' in tables:
            print("   ✅ spot_prices table created")
        else:
            print("   ❌ spot_prices table NOT found")
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()