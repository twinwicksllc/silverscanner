#!/usr/bin/env python3
"""Test Alpha Vantage tie-breaker with simulated API key"""

import os
import sys
from unittest.mock import patch, MagicMock
from database.models import DatabaseManager, PriceHistory
from modules.spot_price import SilverSpotPrice

def test_alpha_vantage_tiebreaker():
    print('=' * 70)
    print('ALPHA VANTAGE TIE-BREAKER SIMULATION')
    print('=' * 70)
    
    # Simulate Alpha Vantage API key
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'TEST_KEY_12345'
    
    # Mock the Alpha Vantage API response
    mock_response_data = {
        'Realtime Currency Exchange Rate': {
            '1. From_Currency Code': 'XAG',
            '2. From_Currency Name': 'Silver',
            '3. To_Currency Code': 'USD',
            '4. To_Currency Name': 'United States Dollar',
            '5. Exchange Rate': '112.50',
            '6. Last Refreshed': '2024-01-27 22:48:00',
            '7. Time Zone': 'UTC'
        }
    }
    
    # Mock the requests.get to return our test data
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Import config after setting env var
        import importlib
        import config
        importlib.reload(config)
        
        print(f'\n1. Configuration:')
        print('-' * 70)
        if config.Config.ALPHA_VANTAGE_API_KEY:
            print(f'   ✅ ALPHA_VANTAGE_API_KEY is set')
        
        # Test the Alpha Vantage fetch directly
        print(f'\n2. Testing Alpha Vantage API Call:')
        print('-' * 70)
        db = DatabaseManager()
        spot_price = SilverSpotPrice(db_manager=db)
        
        # Call Alpha Vantage directly
        av_price = spot_price._fetch_from_alpha_vantage()
        
        if av_price:
            print(f'   ✅ Alpha Vantage returned: ${av_price:.2f}/oz')
        else:
            print(f'   ❌ Alpha Vantage failed to return price')
        
        # Simulate price discrepancy scenario
        print(f'\n3. Simulating Price Discrepancy Scenario:')
        print('-' * 70)
        print(f'   JM Bullion: $103.75/oz')
        print(f'   SD Bullion: $111.95/oz')
        print(f'   Difference: $8.20 (>5% threshold)')
        print(f'   Alpha Vantage: ${av_price:.2f}/oz')
        
        jm_price = 103.75
        sd_price = 111.95
        fallback_price = av_price if av_price else 112.50
        
        jm_diff = abs(jm_price - fallback_price)
        sd_diff = abs(sd_price - fallback_price)
        
        print(f'\n   JM Bullion difference from Alpha Vantage: ${jm_diff:.2f}')
        print(f'   SD Bullion difference from Alpha Vantage: ${sd_diff:.2f}')
        
        if jm_diff < sd_diff:
            print(f'\n   ✅ JM Bullion is closer to Alpha Vantage - would use JM Bullion')
        else:
            print(f'\n   ✅ SD Bullion is closer to Alpha Vantage - would use SD Bullion')
        
        print(f'\n4. Price History Database Write:')
        print('-' * 70)
        
        # Manually test price history write
        session = db.get_session()
        
        # Create test entry
        test_entry = PriceHistory(
            price=fallback_price,
            source='Alpha Vantage (test)',
            timestamp=None
        )
        
        session.add(test_entry)
        session.commit()
        
        # Query it back
        saved_entry = session.query(PriceHistory).order_by(PriceHistory.timestamp.desc()).first()
        
        if saved_entry:
            print(f'   ✅ Successfully wrote to price_history table:')
            print(f'      Price: ${saved_entry.price:.2f}/oz')
            print(f'      Source: {saved_entry.source}')
            print(f'      Timestamp: {saved_entry.timestamp}')
            
            # Clean up test entry
            session.delete(saved_entry)
            session.commit()
            print(f'   ✅ Cleaned up test entry')
        else:
            print(f'   ❌ Failed to write to price_history table')
        
        session.close()
    
    print('\n' + '=' * 70)
    print('SIMULATION COMPLETE')
    print('=' * 70)

if __name__ == '__main__':
    test_alpha_vantage_tiebreaker()