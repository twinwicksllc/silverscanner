"""Deal Scanner Module
Main scanning logic that orchestrates the deal detection process
Supports both silver and gold scanning
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from modules.spot_price import SilverSpotPrice
from modules.multi_metal_spot_price import MultiMetalSpotPrice
from modules.ebay_api import eBayAPI
from modules.asw_calculator import ASWCalculator
from modules.gold_calculator import GoldCalculator
from modules.notifications import EmailNotifier
from database.models import DatabaseManager
from config import Config

logger = logging.getLogger(__name__)

class DealScanner:
    """Main deal scanner that coordinates all components and supports multiple metals"""
    
    def __init__(self, metal_type: str = 'silver'):
        """
        Initialize the deal scanner
        Args:
            metal_type: Type of metal to scan for ('silver' or 'gold')
        """
        self.metal_type = metal_type
        self.spot_price = MultiMetalSpotPrice()  # Updated to use multi-metal
        self.ebay_api = eBayAPI()
        self.asw_calculator = ASWCalculator()
        self.gold_calculator = GoldCalculator() if metal_type == 'gold' else None
        self.db_manager = DatabaseManager()
        self.email_notifier = EmailNotifier(self.db_manager)
        self.scan_results = []
        self.items_scanned = 0
        
    def perform_scan(self, metal_type: Optional[str] = None) -> List[Dict]:
        """
        Perform a complete scan for deals (supports both silver and gold)
        Returns list of qualified deals
        
        Args:
            metal_type: Override the default metal type for this scan
        """
        # Use provided metal_type or default to instance metal_type
        scan_metal_type = metal_type or self.metal_type
        
        # Generate scan_id once at the start
        scan_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info("="*60)
        logger.info(f"Starting {scan_metal_type} deal scan")
        logger.info("="*60)
        
        # Get current spot price for the metal
        if scan_metal_type == 'gold':
            price_info = self.spot_price.get_gold_price_info()
        else:
            price_info = self.spot_price.get_silver_price_info()
            
        spot_price = price_info.get('spot_price')
        
        if not spot_price:
            logger.error(f"Cannot perform scan: unable to get {scan_metal_type} spot price")
            return []
        
        logger.info(f"Current {scan_metal_type} spot price: ${spot_price:.2f}/oz")
        logger.info(f"Deal threshold: ${price_info['threshold']:.2f}/oz")
        
        # Test eBay API connection
        if not self.ebay_api.test_connection():
            logger.error("Cannot perform scan: eBay API connection failed")
            return []
        
        # Search eBay listings
        logger.info("Searching eBay listings...")
        if scan_metal_type == 'gold':
            raw_items = self.ebay_api.get_all_gold_listings()
        else:
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
                
                # Calculate based on metal type
                if scan_metal_type == 'gold':
                    # Calculate gold weight and value
                    gold_result = self.gold_calculator.calculate_agw(item_details)
                    
                    if not gold_result['identified']:
                        rejected_count += 1
                        continue
                    
                    # Calculate deal metrics
                    deal_metrics = self.gold_calculator.calculate_deal_metrics(
                        item_details, gold_result, spot_price
                    )
                    
                    # Validate deal
                    if not self.gold_calculator.validate_deal(item_details, deal_metrics):
                        rejected_count += 1
                        continue
                    
                    # Combine all data
                    deal = {
                        **item_details,
                        'metal_type': 'gold',
                        'gold_info': gold_result,
                        'metrics': deal_metrics,
                        'scan_id': scan_id,
                        'qualified_at': datetime.now().isoformat()
                    }
                    
                else:
                    # Silver logic (existing)
                    asw_result = self.asw_calculator.calculate_asw(item_details)
                    
                    if not asw_result['identified']:
                        rejected_count += 1
                        continue
                    
                    # Calculate deal metrics
                    deal_metrics = self.asw_calculator.calculate_deal_metrics(
                        item_details, asw_result, spot_price
                    )
                    
                    # Check if it qualifies as a deal
                    if not self.asw_calculator.validate_deal(item_details, deal_metrics):
                        rejected_count += 1
                        continue
                    
                    # Combine all data
                    deal = {
                        **item_details,
                        'metal_type': 'silver',
                        'asw_info': asw_result,
                        'metrics': deal_metrics,
                        'scan_id': scan_id,
                        'qualified_at': datetime.now().isoformat()
                    }
                
                qualified_deals.append(deal)
                
                # Log based on metal type
                if scan_metal_type == 'gold':
                    logger.info(f"✓ QUALIFIED GOLD: {item_details['title'][:50]}... "
                               f"(${deal_metrics['cost_per_oz']:.2f}/oz, "
                               f"{deal_metrics['discount_percent']:.1f}% off)")
                else:
                    logger.info(f"✓ QUALIFIED SILVER: {item_details['title'][:50]}... "
                               f"(${deal_metrics['cost_per_oz']:.2f}/oz, "
                               f"{deal_metrics['discount_percent']:.1f}% off)")
                
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                continue
        
        # Sort deals by discount percentage (best deals first)
        qualified_deals.sort(
            key=lambda x: x['metrics']['discount_percent'],
            reverse=True
        )
        
        logger.info("="*60)
        logger.info(f"Scan complete: {len(qualified_deals)} {scan_metal_type} deals found, "
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
        
        # Remove expired deals (listing has ended)
        expired_count = self.db_manager.remove_expired_deals()
        if expired_count > 0:
            logger.info(f"Removed {expired_count} expired deals")
        
        # Cleanup stale deals (not seen in recent scans - likely sold)
        stale_count = self.db_manager.cleanup_stale_deals(current_scan_item_ids, max_age_hours=24)
        if stale_count > 0:
            logger.info(f"Removed {stale_count} stale deals")
        
        # Store scan_id for get_deal_summary()
        self.scan_id = scan_id
        
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
                'coin_types': [],
                'metal_type': self.metal_type
            }
        
        discounts = [deal['metrics']['discount_percent'] for deal in self.scan_results]
        total_savings = 0.0
        
        # Calculate total savings based on metal type
        for deal in self.scan_results:
            if deal.get('metal_type') == 'gold':
                gold_weight = deal.get('gold_info', {}).get('gold_weight_oz', 0)
                total_savings += deal['metrics']['savings_per_oz'] * gold_weight
            else:
                silver_weight = deal.get('asw_info', {}).get('asw', 0)
                total_savings += deal['metrics']['savings_per_oz'] * silver_weight
        
        # Collect item types
        item_types = {}
        for deal in self.scan_results:
            if deal.get('metal_type') == 'gold':
                item_name = deal.get('gold_info', {}).get('purity_str', 'Unknown')
            else:
                item_name = deal.get('asw_info', {}).get('coin_name', 'Unknown')
            item_types[item_name] = item_types.get(item_name, 0) + 1
        
        return {
            'total_deals': len(self.scan_results),
            'best_discount': max(discounts) if discounts else 0.0,
            'avg_discount': sum(discounts) / len(discounts) if discounts else 0.0,
            'total_savings': total_savings,
            'item_types': item_types,
            'metal_type': self.metal_type,
            'scan_time': datetime.now().isoformat(),
            'scan_id': getattr(self, 'scan_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        }
    
    def format_deal_for_display(self, deal: Dict) -> Dict:
        """
        Format deal data for display in web interface
        """
        base_data = {
            'title': deal['title'],
            'price': deal['price'],
            'shipping_cost': deal['shipping_cost'],
            'total_cost': deal['total_cost'],
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
            'metal_type': deal.get('metal_type', 'silver')
        }
        
        # Add metal-specific information
        if deal.get('metal_type') == 'gold':
            base_data.update({
                'item_name': deal.get('gold_info', {}).get('purity_str', 'Unknown'),
                'metal_weight_oz': deal.get('gold_info', {}).get('gold_weight_oz', 0),
                'metal_purity': deal.get('gold_info', {}).get('purity_decimal', 0),
                'confidence': deal.get('gold_info', {}).get('confidence', 0)
            })
        else:
            base_data.update({
                'coin_name': deal.get('asw_info', {}).get('coin_name', 'Unknown'),
                'metal_weight_oz': deal.get('asw_info', {}).get('asw', 0),
                'metal_purity': deal.get('asw_info', {}).get('purity', 0.9),
                'confidence': deal.get('asw_info', {}).get('confidence', 0)
            })
        
        return base_data
    
    def get_all_formatted_deals(self) -> List[Dict]:
        """
        Get all deals formatted for display
        """
        return [self.format_deal_for_display(deal) for deal in self.scan_results]