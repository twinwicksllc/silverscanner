#!/usr/bin/env python3
"""Force spot price refresh and verify two-key logic"""

import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database.models import DatabaseManager, PriceHistory
from modules.spot_price import SilverSpotPrice
from sqlalchemy import desc

def force_refresh_and_verify():
    print('=' * 80)
    print('FORCE SPOT PRICE REFRESH & TWO-KEY VERIFICATION')
    print('=' * 80)
    
    # Initialize components
    db = DatabaseManager()
    spot_price = SilverSpotPrice(db_manager=db)
    
    print(f'\n1. Configuration Check:')
    print('-' * 80)
    print(f'   ALPHA_VANTAGE_API_KEY: {"✓ Set" if Config.ALPHA_VANTAGE_API_KEY else "✗ Not set"}')
    print(f'   SPOT_PRICE_CACHE_MINUTES: {Config.SPOT_PRICE_CACHE_MINUTES}')
    print(f'   ALPHA_VANTAGE_RATE_LIMIT_MINUTES: {Config.ALPHA_VANTAGE_RATE_LIMIT_MINUTES}')
    print(f'   USER_TIMEZONE: {Config.USER_TIMEZONE}')
    
    # Force refresh to bypass cache
    print(f'\n2. Forcing Fresh Spot Price (bypassing cache):')
    print('-' * 80)
    
    start_time = datetime.now()
    price = spot_price.get_spot_price(force_refresh=True)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if price:
        print(f'   ✅ Fresh price fetched: ${price:.2f}/oz')
        print(f'   ⏱ Time elapsed: {elapsed:.2f} seconds')
    else:
        print(f'   ❌ Failed to fetch fresh price')
        return
    
    # Get detailed price info
    price_info = spot_price.get_price_info()
    print(f'\n3. Price Details:')
    print('-' * 80)
    print(f'   Price: ${price_info.get("price", "N/A")}/oz')
    print(f'   Source: {price_info.get("source", "N/A")}')
    print(f'   Threshold: ${price_info.get("threshold", "N/A")}/oz')
    
    # Check Alpha Vantage rate limiting state
    print(f'\n4. Alpha Vantage Rate Limiting:')
    print('-' * 80)
    if spot_price.alpha_vantage_last_call:
        time_since = datetime.now() - spot_price.alpha_vantage_last_call
        print(f'   Last call: {spot_price.alpha_vantage_last_call.strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'   Time since: {time_since.total_seconds()/60:.1f} minutes ago')
        print(f'   Rate limit: {Config.ALPHA_VANTAGE_RATE_LIMIT_MINUTES} minutes')
    else:
        print(f'   No Alpha Vantage calls yet')
    
    # Verify database write
    print(f'\n5. Supabase Price History Verification:')
    print('-' * 80)
    
    session = db.get_session()
    
    # Get latest price history entry
    latest = session.query(PriceHistory).order_by(desc(PriceHistory.timestamp)).first()
    
    if latest:
        print(f'   ✅ Latest entry in price_history:')
        print(f'      Price: ${latest.price:.2f}/oz')
        print(f'      Source: {latest.source}')
        print(f'      Timestamp: {latest.timestamp}')
        
        # Verify it matches our fetched price
        if abs(latest.price - price) < 0.01:
            print(f'   ✅ Database price matches fetched price (${price:.2f}/oz)')
        else:
            print(f'   ⚠ Database price (${latest.price:.2f}) differs from fetched price (${price:.2f})')
        
        # Get recent entries
        recent = session.query(PriceHistory).order_by(desc(PriceHistory.timestamp)).limit(5).all()
        print(f'\n   Recent price history (last 5 entries):')
        for i, entry in enumerate(recent, 1):
            print(f'      {i}. ${entry.price:.2f}/oz - {entry.source} - {entry.timestamp}')
        
    else:
        print(f'   ❌ No entries found in price_history table')
    
    # Get total count
    count = session.query(PriceHistory).count()
    print(f'\n   Total entries in price_history: {count}')
    
    session.close()
    
    print('\n' + '=' * 80)
    print('VERIFICATION COMPLETE')
    print('=' * 80)

if __name__ == '__main__':
    force_refresh_and_verify()