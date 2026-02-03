"""
Deal Scanner Module
Main scanning logic that orchestrates the deal detection process
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from modules.spot_price import SilverSpotPrice
from modules.ebay_api import eBayAPI
from modules.asw_calculator import ASWCalculator
from modules.notifications import EmailNotifier
from database.models import DatabaseManager
from config import Config

logger = logging.getLogger(__name__)

class DealScanner:
    """Main deal scanner that coordinates all components"""
    
    def __init__(self):
        self.spot_price = SilverSpotPrice()
        self.ebay_api = eBayAPI()
        self.asw_calculator = ASWCalculator()
        self.db_manager = DatabaseManager()
        self.email_notifier = EmailNotifier(self.db_manager)
        self.scan_results = []
        self.items_scanned = 0
        
    def perform_scan(self) -> List[Dict]:
        """
        Perform a complete scan for silver deals
        Returns list of qualified deals
        """
        logger.info("="*60)
        logger.info("Starting silver deal scan")
        logger.info("="*60)
        
        # Get current spot price
        price_info = self.spot_price.get_price_info()
        spot_price = price_info['spot_price']
        
        if not spot_price:
            logger.error("Cannot perform scan: unable to get spot price")
            return []
        
        logger.info(f"Current spot price: ${spot_price:.2f}/oz")
        logger.info(f"Deal threshold: ${price_info['threshold']:.2f}/oz")
        
        # Test eBay API connection
        if not self.ebay_api.test_connection():
            logger.error("Cannot perform scan: eBay API connection failed")
            return []
        
        # Search eBay listings
        logger.info("Searching eBay listings...")
        raw_items = self.ebay_api.get_all_silver_listings()
        
        if not raw_items:
            logger.warning("No eBay listings found")
            return []
        
        logger.info(f"Processing {len(raw_items)} listings...")
        
        # Process each item
        qualified_deals = []
        rejected_count = 0
        current_scan_item_ids = set()  # Track all item IDs for expunge routine
        
        for item in raw_items:
            # Count every item processed
            self.items_scanned += 1
            
            # Track item ID for expunge routine
            item_id = item.get('itemId')
            if item_id:
                current_scan_item_ids.add(item_id)
            try:
                # Extract item details
                item_details = self.ebay_api.extract_item_details(item)
                
                if not item_details:
                    continue
                
                # Calculate ASW
                asw_result = self.asw_calculator.calculate_asw(item_details)
                
                if not asw_result['identified']:
                    rejected_count += 1
                    continue
                
                # Calculate deal metrics
                deal_metrics = self.asw_calculator.calculate_deal_metrics(
                    item_details, asw_result, spot_price
                )
                
                # Check if it qualifies as a deal
                if self.asw_calculator.validate_deal(item_details, deal_metrics):
                    # Combine all data
                    deal = {
                        **item_details,
                        'asw_info': asw_result,
                        'metrics': deal_metrics,
                        'scan_id': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'qualified_at': datetime.now().isoformat()
                    }
                    
                    qualified_deals.append(deal)
                    logger.info(f"✓ QUALIFIED: {item_details['title'][:50]}... "
                               f"(${deal_metrics['cost_per_oz']:.2f}/oz, "
                               f"{deal_metrics['discount_percent']:.1f}% off)")
                else:
                    rejected_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                continue
        
        # Sort deals by discount percentage (best deals first)
        qualified_deals.sort(
            key=lambda x: x['metrics']['discount_percent'],
            reverse=True
        )
        
        logger.info("="*60)
        logger.info(f"Scan complete: {len(qualified_deals)} deals found, "
                   f"{rejected_count} items rejected")
        logger.info("="*60)
        
        # Send instant fire alarm alerts for exceptional deals (greater than or equal to 15% discount)
        fire_alarm_count = 0
        for deal in qualified_deals:
            discount = deal['metrics']['discount_percent']
            if discount >= 15.0:
                logger.info(f"Fire alarm triggered for {deal['title'][:50]}... ({discount:.1f}% off)")
                if self.email_notifier.send_fire_alarm_alert(deal):
                    fire_alarm_count += 1
        
        if fire_alarm_count > 0:
            logger.info(f"Sent {fire_alarm_count} fire alarm alerts")
        
        # Expunge stale hidden deals (sold/expired items)
        expunged_count = self.db_manager.expunge_stale_hidden_deals(current_scan_item_ids)
        if expunged_count > 0:
            logger.info(f"Expunged {expunged_count} stale hidden deals")
        
        # Remove zero-quantity deals (sold-out items)
        removed_count = self.db_manager.remove_zero_quantity_deals()
        if removed_count > 0:
            logger.info(f"Removed {removed_count} sold-out deals")
        
        self.scan_results = qualified_deals
        return qualified_deals
    
    def get_deal_summary(self) -> Dict:
        """
        Get summary of last scan results
        """
        if not self.scan_results:
            return {
                'total_deals': 0,
                'best_discount': 0.0,
                'avg_discount': 0.0,
                'total_savings': 0.0,
                'coin_types': []
            }
        
        discounts = [deal['metrics']['discount_percent'] for deal in self.scan_results]
        total_savings = sum(deal['metrics']['savings_per_oz'] * deal['asw_info']['asw'] 
                          for deal in self.scan_results)
        
        coin_types = {}
        for deal in self.scan_results:
            coin_name = deal['asw_info']['coin_name']
            coin_types[coin_name] = coin_types.get(coin_name, 0) + 1
        
        return {
            'total_deals': len(self.scan_results),
            'best_discount': max(discounts) if discounts else 0.0,
            'avg_discount': sum(discounts) / len(discounts) if discounts else 0.0,
            'total_savings': total_savings,
            'coin_types': coin_types,
            'scan_time': datetime.now().isoformat()
        }
    
    def format_deal_for_display(self, deal: Dict) -> Dict:
        """
        Format deal data for display in web interface
        """
        return {
            'title': deal['title'],
            'price': deal['price'],
            'shipping_cost': deal['shipping_cost'],
            'total_cost': deal['total_cost'],
            'coin_name': deal['asw_info']['coin_name'],
            'silver_weight_oz': deal['asw_info']['asw'],
            'cost_per_oz': deal['metrics']['cost_per_oz'],
            'discount_percent': deal['metrics']['discount_percent'],
            'spot_price': deal['metrics']['spot_price'],
            'threshold': deal['metrics']['threshold'],
            'savings_per_oz': deal['metrics']['savings_per_oz'],
            'seller_username': deal['seller_username'],
            'seller_feedback': deal['seller_feedback'],
            'condition': deal['condition'],
            'item_url': deal['item_url'],
            'image_url': deal['image_url'],
            'qualified_at': deal['qualified_at'],
            'confidence': deal['asw_info']['confidence']
        }
    
    def get_all_formatted_deals(self) -> List[Dict]:
        """
        Get all deals formatted for display
        """
        return [self.format_deal_for_display(deal) for deal in self.scan_results]