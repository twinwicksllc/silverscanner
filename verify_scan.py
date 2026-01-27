#!/usr/bin/env python3
"""Verification script to test spot price fetching and database writes"""

from config import Config
from database.models import DatabaseManager, PriceHistory
from modules.spot_price import SilverSpotPrice
from sqlalchemy import inspect

def run_verification():
    print('=' * 70)
    print('SILVER SCANNER VERIFICATION SCAN')
    print('=' * 70)
    
    # Initialize database and spot price
    db = DatabaseManager()
    spot_price = SilverSpotPrice(db_manager=db)
    
    # Step 1: Fetch Spot Price (forcing refresh)
    print('\n1. Fetching Spot Price (forcing refresh)...')
    print('-' * 70)
    price = spot_price.get_spot_price(force_refresh=True)
    
    if price:
        print(f'   ✅ Spot Price: ${price:.2f}/oz')
    else:
        print('   ❌ Failed to fetch spot price')
        return
    
    # Step 2: Get price info with source
    price_info = spot_price.get_price_info()
    print(f'\n2. Price Details:')
    print('-' * 70)
    print(f'   Source: {price_info.get("source", "Unknown")}')
    print(f'   Updated: {price_info.get("updated", "Unknown")}')
    threshold = price_info.get('threshold')
    if threshold:
        print(f'   Deal Threshold (89%): ${threshold:.2f}/oz')
    
    # Step 3: Database Connection and Tables
    print(f'\n3. Database Connection:')
    print('-' * 70)
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f'   ✅ Connected to database')
        print(f'   Database Type: {db.engine.url.drivername}')
        print(f'   Tables: {", ".join(tables)}')
    except Exception as e:
        print(f'   ❌ Database error: {e}')
        return
    
    # Step 4: Check Price History Table
    print(f'\n4. Price History Table:')
    print('-' * 70)
    
    if 'price_history' in tables:
        try:
            # Get latest price history entry
            session = db.get_session()
            latest = session.query(PriceHistory).order_by(PriceHistory.timestamp.desc()).first()
            
            if latest:
                print(f'   ✅ Latest price history entry:')
                print(f'      Price: ${latest.price:.2f}/oz')
                print(f'      Source: {latest.source}')
                print(f'      Timestamp: {latest.timestamp}')
            else:
                print('   ⚠ No price history entries found')
            
            # Get count of entries
            count = session.query(PriceHistory).count()
            print(f'   Total entries in price_history: {count}')
            
            session.close()
            
        except Exception as e:
            print(f'   ❌ Error querying price_history: {e}')
    else:
        print('   ❌ price_history table does not exist')
    
    # Step 5: Verify Alpha Vantage Configuration
    print(f'\n5. Alpha Vantage Configuration:')
    print('-' * 70)
    if Config.ALPHA_VANTAGE_API_KEY:
        masked_key = Config.ALPHA_VANTAGE_API_KEY[:8] + '...' if len(Config.ALPHA_VANTAGE_API_KEY) > 8 else '...'
        print(f'   ✅ ALPHA_VANTAGE_API_KEY is set: {masked_key}')
    else:
        print(f'   ⚠ ALPHA_VANTAGE_API_KEY is NOT set')
    
    print('\n' + '=' * 70)
    print('VERIFICATION COMPLETE')
    print('=' * 70)

if __name__ == '__main__':
    run_verification()