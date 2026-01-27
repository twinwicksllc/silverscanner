"""
Comprehensive test script for Supabase integration and email notifications
"""

import os
import logging
from datetime import datetime
from database.models import DatabaseManager
from modules.spot_price import SilverSpotPrice
from modules.notifications import EmailNotifier

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test Supabase database connection and table creation"""
    logger.info("="*60)
    logger.info("TEST 1: Database Connection &amp; Table Creation")
    logger.info("="*60)
    
    try:
        db = DatabaseManager()
        logger.info("✅ Database connection successful")
        
        # Check if we're using PostgreSQL or SQLite
        from config import Config
        if Config.DATABASE_URL.startswith('postgresql'):
            logger.info("✅ Using PostgreSQL (Supabase)")
        else:
            logger.info("ℹ️  Using SQLite (local)")
        
        logger.info(f"Database URL: {Config.DATABASE_URL[:30]}...")
        
        # Test a simple query
        session = db.get_session()
        try:
            # Try to query scan history (should work even if empty)
            from database.models import ScanHistory
            count = session.query(ScanHistory).count()
            logger.info(f"✅ Tables accessible - ScanHistory has {count} records")
        finally:
            session.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_spot_price_averaging():
    """Test spot price fetching and averaging from multiple sources"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Spot Price Fetching &amp; Averaging")
    logger.info("="*60)
    
    try:
        db = DatabaseManager()
        spot_price = SilverSpotPrice(db)
        
        # Force refresh to fetch from all sources
        logger.info("Fetching prices from all sources...")
        price = spot_price.get_spot_price(force_refresh=True)
        
        if price:
            logger.info(f"✅ Successfully fetched and averaged spot price: ${price:.2f}/oz")
            
            # Check cache for details
            if 'spot_price' in spot_price.cache:
                cache_data = spot_price.cache['spot_price']
                if 'individual_prices' in cache_data:
                    individual = cache_data['individual_prices']
                    logger.info(f"   Individual prices: {', '.join([f'${p:.2f}' for p in individual])}")
                    logger.info(f"   Sources used: {cache_data.get('source', 'Unknown')}")
                    logger.info(f"   Number of sources: {len(individual)}")
            
            return True
        else:
            logger.error("❌ Failed to fetch spot price")
            return False
            
    except Exception as e:
        logger.error(f"❌ Spot price test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fire_alarm_email():
    """Test fire alarm email notification"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Fire Alarm Email Notification")
    logger.info("="*60)
    
    try:
        db = DatabaseManager()
        notifier = EmailNotifier(db)
        
        if not notifier.enabled:
            logger.warning("⚠️  Email notifications are disabled")
            logger.warning("   Please set the following environment variables:")
            logger.warning("   - ENABLE_EMAIL_NOTIFICATIONS=True")
            logger.warning("   - SMTP_USERNAME=your-email@gmail.com")
            logger.warning("   - SMTP_PASSWORD=your-app-password")
            logger.warning("   - EMAIL_TO=a76marine@gmail.com")
            return False
        
        # Create test deal with >15% discount
        test_deal = {
            'item_id': f'TEST_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'title': 'TEST: Walking Liberty Half Dollar 90% Silver - Excellent Deal!',
            'price': 8.50,
            'shipping_cost': 1.50,
            'total_cost': 10.00,
            'seller_username': 'test_seller_99',
            'seller_feedback': 99.8,
            'condition': 'Very Good',
            'item_url': 'https://www.ebay.com/itm/TEST123456',
            'image_url': 'https://example.com/image.jpg',
            'qualified_at': datetime.now().isoformat(),
            'asw_info': {
                'coin_type': 'walking_liberty_half',
                'coin_name': 'Walking Liberty Half Dollar',
                'asw': 0.36169,
                'quantity': 1,
                'face_value': 0.50,
                'confidence': 0.95
            },
            'metrics': {
                'spot_price': 30.00,
                'cost_per_oz': 27.65,
                'discount_percent': 17.8,
                'savings_per_oz': 5.35,
                'threshold': 25.50
            }
        }
        
        logger.info("Sending test fire alarm email...")
        logger.info(f"Test deal: {test_deal['title']}")
        logger.info(f"Discount: {test_deal['metrics']['discount_percent']:.1f}%")
        logger.info(f"Recipient: {os.getenv('EMAIL_TO', 'Not set')}")
        
        success = notifier.send_fire_alarm_alert(test_deal)
        
        if success:
            logger.info("✅ Fire alarm email sent successfully!")
            logger.info("   Check your inbox at a76marine@gmail.com")
            logger.info("   Subject: 🚨 [EXCEPTIONAL DEAL] - TEST: Walking Liberty Half Dollar...")
            return True
        else:
            logger.error("❌ Failed to send fire alarm email")
            return False
            
    except Exception as e:
        logger.error(f"❌ Email test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SUPABASE &amp; EMAIL NOTIFICATION TEST SUITE")
    print("="*60 + "\n")
    
    results = {
        'Database Connection': test_database_connection(),
        'Spot Price Averaging': test_spot_price_averaging(),
        'Fire Alarm Email': test_fire_alarm_email()
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Check logs above")
    print("="*60 + "\n")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)