"""
Test script for Two-Key Verification spot price system
"""

import logging
from modules.spot_price import SilverSpotPrice
from database.models import DatabaseManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_two_key_verification():
    """Test the two-key verification system"""
    print("\n" + "="*70)
    print("TWO-KEY VERIFICATION SYSTEM TEST")
    print("="*70 + "\n")
    
    db = DatabaseManager()
    spot_price = SilverSpotPrice(db)
    
    print("Testing spot price fetching with two-key verification...\n")
    
    # Force refresh to fetch from all sources
    price = spot_price.get_spot_price(force_refresh=True)
    
    print("\n" + "="*70)
    if price:
        print(f"✅ SUCCESS: Verified spot price = ${price:.2f}/oz")
        
        # Show cache details
        if 'spot_price' in spot_price.cache:
            cache_data = spot_price.cache['spot_price']
            print(f"Source: {cache_data.get('source', 'Unknown')}")
            print(f"Timestamp: {cache_data.get('timestamp')}")
    else:
        print("❌ FAILED: Could not verify spot price")
    
    print("="*70 + "\n")
    
    return price is not None

if __name__ == '__main__':
    success = test_two_key_verification()
    exit(0 if success else 1)