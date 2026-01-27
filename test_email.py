"""
Test script for email notification system
"""

import os
import logging
from modules.notifications import EmailNotifier
from database.models import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test deal data
test_deal = {
    'item_id': 'TEST123456',
    'title': 'Walking Liberty Half Dollar 90% Silver Coin - Great Condition',
    'price': 8.50,
    'shipping_cost': 1.50,
    'total_cost': 10.00,
    'seller_username': 'test_seller',
    'seller_feedback': 99.5,
    'condition': 'Very Good',
    'item_url': 'https://www.ebay.com/itm/TEST123456',
    'image_url': 'https://example.com/image.jpg',
    'qualified_at': '2024-01-27T12:00:00',
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

test_deals = [test_deal]

def test_fire_alarm():
    """Test fire alarm alert"""
    logger.info("Testing Fire Alarm Alert...")
    
    db = DatabaseManager()
    notifier = EmailNotifier(db)
    
    if not notifier.enabled:
        logger.warning("Email notifications are disabled. Set environment variables to test:")
        logger.warning("  ENABLE_EMAIL_NOTIFICATIONS=True")
        logger.warning("  SMTP_USERNAME=your-email@gmail.com")
        logger.warning("  SMTP_PASSWORD=your-app-password")
        logger.warning("  EMAIL_TO=recipient@example.com")
        return False
    
    success = notifier.send_fire_alarm_alert(test_deal)
    
    if success:
        logger.info("✅ Fire alarm sent successfully!")
    else:
        logger.error("❌ Failed to send fire alarm")
    
    return success

def test_digest():
    """Test digest email"""
    logger.info("Testing Digest Email...")
    
    db = DatabaseManager()
    notifier = EmailNotifier(db)
    
    if not notifier.enabled:
        logger.warning("Email notifications are disabled. Set environment variables to test.")
        return False
    
    success = notifier.send_digest_email(test_deals)
    
    if success:
        logger.info("✅ Digest sent successfully!")
    else:
        logger.error("❌ Failed to send digest")
    
    return success

def test_html_generation():
    """Test HTML template generation without sending"""
    logger.info("Testing HTML Template Generation...")
    
    db = DatabaseManager()
    notifier = EmailNotifier(db)
    
    # Test fire alarm HTML
    fire_alarm_html = notifier._create_fire_alarm_html(test_deal)
    logger.info(f"Fire alarm HTML length: {len(fire_alarm_html)} characters")
    
    # Test digest HTML
    digest_html = notifier._create_digest_html(test_deals)
    logger.info(f"Digest HTML length: {len(digest_html)} characters")
    
    # Save to files for inspection
    with open('/tmp/fire_alarm_test.html', 'w') as f:
        f.write(fire_alarm_html)
    logger.info("Fire alarm HTML saved to /tmp/fire_alarm_test.html")
    
    with open('/tmp/digest_test.html', 'w') as f:
        f.write(digest_html)
    logger.info("Digest HTML saved to /tmp/digest_test.html")
    
    return True

if __name__ == '__main__':
    print("\n" + "="*60)
    print("EMAIL NOTIFICATION SYSTEM TEST")
    print("="*60 + "\n")
    
    # Test HTML generation (always works)
    print("\n1. Testing HTML Template Generation...")
    test_html_generation()
    
    # Test actual email sending (requires env vars)
    print("\n2. Testing Fire Alarm Alert...")
    test_fire_alarm()
    
    print("\n3. Testing Digest Email...")
    test_digest()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")