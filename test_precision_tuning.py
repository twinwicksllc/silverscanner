"""
Test script for Final Precision Tuning features
Tests: UPSERT logic, time_listed capture, and expunge routine
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from database.models import DatabaseManager, Deal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_upsert_logic():
    """Test that UPSERT logic preserves is_hidden flag"""
    logger.info("=" * 60)
    logger.info("TEST 1: UPSERT Logic - Preserving is_hidden flag")
    logger.info("=" * 60)
    
    db = DatabaseManager()
    
    # Create test deal data
    test_deal_data = {
        'item_id': 'TEST_ITEM_001',
        'title': 'Test Deal for UPSERT',
        'price': 100.0,
        'shipping_cost': 5.0,
        'total_cost': 105.0,
        'asw_info': {
            'coin_type': 'Test Coin',
            'coin_name': 'Test Silver Round',
            'asw': 1.0,
            'quantity': 1,
            'confidence': 0.95
        },
        'metrics': {
            'spot_price': 120.0,
            'cost_per_oz': 105.0,
            'discount_percent': 12.5,
            'savings_per_oz': 15.0,
            'threshold': 106.8
        },
        'seller_username': 'test_seller',
        'seller_feedback': 99.0,
        'condition': 'New',
        'item_url': 'https://test.com/item/001',
        'image_url': 'https://test.com/image/001.jpg',
        'time_listed': datetime.utcnow(),
        'scan_id': 'TEST_SCAN_001'
    }
    
    # Save initial deal
    result1 = db.save_deal(test_deal_data)
    logger.info(f"Initial save result: {result1}")
    
    # Verify deal was saved
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_001').first()
    logger.info(f"Deal exists: {deal is not None}")
    logger.info(f"Deal is_hidden: {deal.is_hidden}")
    session.close()
    
    # Hide the deal
    db.hide_deal('TEST_ITEM_001')
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_001').first()
    logger.info(f"Deal after hide - is_hidden: {deal.is_hidden}")
    session.close()
    
    # Update the deal (simulate new scan finding same item)
    test_deal_data['title'] = 'Test Deal for UPSERT (Updated)'
    test_deal_data['price'] = 102.0
    test_deal_data['total_cost'] = 107.0
    result2 = db.save_deal(test_deal_data)
    logger.info(f"Update save result: {result2}")
    
    # Verify is_hidden flag was preserved
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_001').first()
    logger.info(f"Deal after update - is_hidden: {deal.is_hidden}")
    logger.info(f"Deal title updated: {deal.title}")
    logger.info(f"Deal price updated: {deal.price}")
    assert deal.is_hidden == True, "is_hidden flag should be preserved during update!"
    assert deal.title == 'Test Deal for UPSERT (Updated)', "Title should be updated!"
    session.close()
    
    # Clean up
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_001').first()
    if deal:
        session.delete(deal)
        session.commit()
    session.close()
    
    logger.info("✅ TEST 1 PASSED: UPSERT logic preserves is_hidden flag\n")
    return True

def test_time_listed_capture():
    """Test that time_listed captures eBay listing start time"""
    logger.info("=" * 60)
    logger.info("TEST 2: time_listed Capture from eBay API")
    logger.info("=" * 60)
    
    db = DatabaseManager()
    
    # Create test deal with explicit time_listed
    test_time = datetime.utcnow() - timedelta(hours=2)  # Listed 2 hours ago
    test_deal_data = {
        'item_id': 'TEST_ITEM_002',
        'title': 'Test Deal for Time Listed',
        'price': 100.0,
        'shipping_cost': 5.0,
        'total_cost': 105.0,
        'asw_info': {
            'coin_type': 'Test Coin',
            'coin_name': 'Test Silver Round',
            'asw': 1.0,
            'quantity': 1,
            'confidence': 0.95
        },
        'metrics': {
            'spot_price': 120.0,
            'cost_per_oz': 105.0,
            'discount_percent': 12.5,
            'savings_per_oz': 15.0,
            'threshold': 106.8
        },
        'seller_username': 'test_seller',
        'seller_feedback': 99.0,
        'condition': 'New',
        'item_url': 'https://test.com/item/002',
        'image_url': 'https://test.com/image/002.jpg',
        'time_listed': test_time,  # This should be eBay's itemCreationDate
        'scan_id': 'TEST_SCAN_002'
    }
    
    # Save deal
    result = db.save_deal(test_deal_data)
    logger.info(f"Save result: {result}")
    
    # Verify time_listed was saved
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_002').first()
    logger.info(f"Deal time_listed: {deal.time_listed}")
    logger.info(f"Expected time_listed: {test_time}")
    assert deal.time_listed is not None, "time_listed should not be None!"
    
    # Verify time_since_listed calculation uses time_listed, not qualified_at
    deal_dict = db._deal_to_dict(deal)
    logger.info(f"time_since_listed: {deal_dict['time_since_listed']}")
    logger.info(f"qualified_at: {deal_dict['qualified_at']}")
    
    # Should show "2h ago" not "Just now"
    assert 'h ago' in deal_dict['time_since_listed'] or '2h' in deal_dict['time_since_listed'], \
        "time_since_listed should be based on eBay listing time (2h ago)!"
    
    session.close()
    
    # Clean up
    session = db.get_session()
    deal = session.query(Deal).filter_by(item_id='TEST_ITEM_002').first()
    if deal:
        session.delete(deal)
        session.commit()
    session.close()
    
    logger.info("✅ TEST 2 PASSED: time_listed captures eBay listing start time\n")
    return True

def test_expunge_routine():
    """Test that expunge removes stale hidden deals"""
    logger.info("=" * 60)
    logger.info("TEST 3: Expunge Routine - Garbage Collection")
    logger.info("=" * 60)
    
    db = DatabaseManager()
    
    # Create 3 test deals
    test_items = [
        ('TEST_ITEM_003', 'Active Hidden Deal 1'),
        ('TEST_ITEM_004', 'Active Hidden Deal 2'),
        ('TEST_ITEM_005', 'Stale Hidden Deal (should be expunged)')
    ]
    
    for item_id, title in test_items:
        test_deal_data = {
            'item_id': item_id,
            'title': title,
            'price': 100.0,
            'shipping_cost': 5.0,
            'total_cost': 105.0,
            'asw_info': {
                'coin_type': 'Test Coin',
                'coin_name': 'Test Silver Round',
                'asw': 1.0,
                'quantity': 1,
                'confidence': 0.95
            },
            'metrics': {
                'spot_price': 120.0,
                'cost_per_oz': 105.0,
                'discount_percent': 12.5,
                'savings_per_oz': 15.0,
                'threshold': 106.8
            },
            'seller_username': 'test_seller',
            'seller_feedback': 99.0,
            'condition': 'New',
            'item_url': f'https://test.com/item/{item_id}',
            'image_url': f'https://test.com/image/{item_id}.jpg',
            'time_listed': datetime.utcnow(),
            'scan_id': 'TEST_SCAN_003'
        }
        db.save_deal(test_deal_data)
        db.hide_deal(item_id)
    
    # Verify all 3 deals are hidden
    session = db.get_session()
    hidden_deals = session.query(Deal).filter_by(is_hidden=True).filter(
        Deal.item_id.in_([item[0] for item in test_items])
    ).all()
    logger.info(f"Hidden deals before expunge: {len(hidden_deals)}")
    assert len(hidden_deals) == 3, "Should have 3 hidden deals before expunge!"
    session.close()
    
    # Simulate current scan (only 2 items are still active)
    current_scan_item_ids = {'TEST_ITEM_003', 'TEST_ITEM_004'}
    
    # Run expunge
    expunged_count = db.expunge_stale_hidden_deals(current_scan_item_ids)
    logger.info(f"Expunged {expunged_count} stale hidden deals")
    assert expunged_count == 1, "Should expunge exactly 1 stale hidden deal!"
    
    # Verify only 2 hidden deals remain (the active ones)
    session = db.get_session()
    hidden_deals = session.query(Deal).filter_by(is_hidden=True).filter(
        Deal.item_id.in_([item[0] for item in test_items])
    ).all()
    logger.info(f"Hidden deals after expunge: {len(hidden_deals)}")
    remaining_ids = [deal.item_id for deal in hidden_deals]
    logger.info(f"Remaining hidden deal IDs: {remaining_ids}")
    assert len(hidden_deals) == 2, "Should have 2 hidden deals after expunge!"
    assert 'TEST_ITEM_005' not in remaining_ids, "Stale deal should be removed!"
    assert 'TEST_ITEM_003' in remaining_ids, "Active deal 1 should remain!"
    assert 'TEST_ITEM_004' in remaining_ids, "Active deal 2 should remain!"
    session.close()
    
    # Clean up remaining test deals
    session = db.get_session()
    deals = session.query(Deal).filter(
        Deal.item_id.in_([item[0] for item in test_items])
    ).all()
    for deal in deals:
        session.delete(deal)
    session.commit()
    session.close()
    
    logger.info("✅ TEST 3 PASSED: Expunge routine removes stale hidden deals\n")
    return True

def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("FINAL PRECISION TUNING - TEST SUITE")
    logger.info("=" * 60 + "\n")
    
    all_passed = True
    
    try:
        test_upsert_logic()
    except AssertionError as e:
        logger.error(f"❌ TEST 1 FAILED: {e}")
        all_passed = False
    
    try:
        test_time_listed_capture()
    except AssertionError as e:
        logger.error(f"❌ TEST 2 FAILED: {e}")
        all_passed = False
    
    try:
        test_expunge_routine()
    except AssertionError as e:
        logger.error(f"❌ TEST 3 FAILED: {e}")
        all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED!")
        logger.error("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())