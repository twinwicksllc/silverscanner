"""
ASW (Actual Silver Weight) Calculator Module
Calculates silver content and deal metrics for coin listings
"""

import re
import logging
from typing import Dict, Optional, List
from config import Config

logger = logging.getLogger(__name__)

class ASWCalculator:
    """Calculates Actual Silver Weight and deal metrics for silver listings"""
    
    def __init__(self):
        self.asw_values = Config.ASW_VALUES
        self.coin_patterns = self._build_coin_patterns()
        
        # Anti-scam exclusion keywords for silver
        self.exclusion_keywords = [
            'plated', 'filled', 'overlay', 'tone', 'color',
            'replica', 'copy', 'fake', 'costume', 'fashion',
            'imitation', 'silver-colored', 'silver colored',
            'silver tone', 'silver-tone', 'not real silver',
            'not actual silver', 'silver appearance', 'looks like silver',
            'layered', 'vermeil', 'electroplate', 'silver leaf',
            'clad', 'alpacca', 'german silver', 'nickel silver'
        ]
    
    def _build_coin_patterns(self) -> Dict[str, Dict]:
        """
        Build regex patterns for identifying coin types from titles
        """
        patterns = {
            'walking liberty half': {
                'patterns': [
                    r'walking\s+liberty\s+half',
                    r'walker\s+half',
                    r'walking\s+liberty\s+dollar',
                    r'liberty\s+walking\s+half'
                ],
                'asw': 0.36169,
                'name': 'Walking Liberty Half Dollar'
            },
            'barber half': {
                'patterns': [
                    r'barber\s+half',
                    r'barber\s+half\s+dollar',
                    r'1892-1915\s+half'
                ],
                'asw': 0.36169,
                'name': 'Barber Half Dollar'
            },
            'franklin half': {
                'patterns': [
                    r'franklin\s+half',
                    r'franklin\s+half\s+dollar',
                    r'ben\s+franklin\s+half'
                ],
                'asw': 0.36169,
                'name': 'Franklin Half Dollar'
            },
            'peace dollar': {
                'patterns': [
                    r'peace\s+dollar',
                    r'peace\s+silver\s+dollar',
                    r'1921-1935\s+dollar'
                ],
                'asw': 0.77344,
                'name': 'Peace Dollar'
            },
            'morgan dollar': {
                'patterns': [
                    r'morgan\s+dollar',
                    r'morgan\s+silver\s+dollar',
                    r'1878-1904\s+dollar',
                    r'1921\s+morgan'
                ],
                'asw': 0.77344,
                'name': 'Morgan Dollar'
            },
            'kennedy half 1964': {
                'patterns': [
                    r'1964\s+kennedy\s+half',
                    r'kennedy\s+half\s+1964',
                    r'90%\s+kennedy\s+half'
                ],
                'asw': 0.36169,
                'name': '1964 Kennedy Half Dollar (90%)'
            },
            'junk silver': {
                'patterns': [
                    r'junk\s+silver',
                    r'constitutional\s+silver',
                    r'90%\s+junk',
                    r'pre-65\s+silver',
                    r'face\s+value.*silver'
                ],
                'asw': 0.7234,  # per $1 face value
                'name': '90% Junk Silver (per $1 face)'
            },
            'silver eagle': {
                'patterns': [
                    r'american\s+silver\s+eagle',
                    r'silver\s+eagle',
                    r'\base\b.*silver'
                ],
                'asw': 1.0,
                'name': 'American Silver Eagle'
            },
            'silver maple': {
                'patterns': [
                    r'canadian\s+silver\s+maple',
                    r'silver\s+maple',
                    r'maple\s+leaf.*silver'
                ],
                'asw': 1.0,
                'name': 'Silver Maple Leaf'
            },
            'silver buffalo': {
                'patterns': [
                    r'silver\s+buffalo',
                    r'buffalo\s+silver'
                ],
                'asw': 1.0,
                'name': 'Silver Buffalo'
            }
        }
        
        return patterns

    def _is_excluded(self, text: str) -> bool:
        """Check if item contains exclusion keywords"""
        return any(kw in text.lower() for kw in self.exclusion_keywords)

    def _extract_weight(self, text: str) -> Optional[Dict]:
        """Extract weight from text, converting to troy oz"""
        text = text.lower()
        
        patterns = [
            # Troy oz
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?oz(?:s|troy)?', 'troy_oz', 1.0),
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?ounce', 'troy_oz', 1.0),
            # Grams
            (r'(\d+(?:\.\d+)?)\s*g\b(?!rain)', 'grams', 1/31.1035),
            (r'(\d+(?:\.\d+)?)\s*grams?', 'grams', 1/31.1035),
            # Kilos
            (r'(\d+(?:\.\d+)?)\s*kg\b', 'kilos', 32.1507),
            (r'(\d+(?:\.\d+)?)\s*kilo(?:gram)?s?', 'kilos', 32.1507),
        ]
        
        for pattern, unit, conversion in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    weight = float(match.group(1))
                    if 0.001 < weight < 5000:  # Sanity check
                        return {
                            'weight': weight,
                            'unit': unit,
                            'weight_oz': weight * conversion
                        }
                except (ValueError, IndexError):
                    pass
        
        return None

    def _identify_generic_silver(self, text: str) -> Dict:
        """Identify generic silver rounds and bars by extracting weight"""
        text_lower = text.lower()
        
        # Look for "silver" AND ("round" OR "bar" OR bullion keywords)
        is_silver = 'silver' in text_lower or '.999' in text_lower
        is_bullion = any(kw in text_lower for kw in ['round', 'bar', 'bullion', 'ingot', 'coin'])
        
        if not (is_silver and is_bullion):
            return {'identified': False}
            
        weight_info = self._extract_weight(text_lower)
        if not weight_info:
            return {'identified': False}
            
        weight_oz = weight_info['weight_oz']
        item_type = 'Silver Bar' if 'bar' in text_lower else 'Silver Round' if 'round' in text_lower else 'Silver Bullion'
        
        return {
            'identified': True,
            'type': f'generic_{item_type.lower().replace(" ", "_")}',
            'name': f'{weight_info["weight"]} {weight_info["unit"]} {item_type}',
            'asw': weight_oz,
            'confidence': 0.75
        }

    def identify_coin_type(self, title: str, description: str = '') -> Optional[Dict]:
        """
        Identify coin type from title and description
        Returns dict with coin info or None if not identified
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ''
        text_to_search = f"{title_lower} {desc_lower}"
        
        # 1. Check specific patterns (Morgan, Peace, Eagles, etc.)
        for coin_key, coin_info in self.coin_patterns.items():
            for pattern in coin_info['patterns']:
                if re.search(pattern, text_to_search):
                    logger.debug(f"Identified '{coin_info['name']}' from pattern: {pattern}")
                    return {
                        'type': coin_key,
                        'name': coin_info['name'],
                        'base_asw': coin_info['asw']
                    }
        
        # 2. Try generic weight extraction for rounds/bars
        generic_info = self._identify_generic_silver(text_to_search)
        if generic_info['identified']:
            return {
                'type': generic_info['type'],
                'name': generic_info['name'],
                'base_asw': generic_info['asw']
            }
            
        return None
    
    def extract_face_value(self, title: str, description: str = '') -> float:
        """
        Extract face value for junk silver listings
        Returns face value in dollars
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ''
        text_to_search = f"{title_lower} {desc_lower}"
        
        # Look for patterns like "$10 face value", "5 face", "$20 lot"
        patterns = [
            r'\$(\d+(?:\.\d+)?)\s*(?:face|lot|value|fv)',
            r'(\d+(?:\.\d+)?)\s*\$\s*(?:face|lot|value|fv)',
            r'(\d+)\s*(?:face|lot|value|fv)\s*\$',
            r'(\d+)\s*dollar\s*(?:face|lot|value)',
            r'(\d+)\s*oz\s*(?:face|fv)',
            r'(\d+)\s*roll.*90%',
            r'roll.*of\s*(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_to_search)
            for match in matches:
                try:
                    value = float(match)
                    if value > 0 and value <= 1000:  # Reasonable range
                        logger.debug(f"Extracted face value: ${value}")
                        return value
                except (ValueError, TypeError):
                    continue
        
        return 0.0
    
    def extract_quantity(self, title: str, description: str = '') -> int:
        """
        Extract quantity for multiple coin listings
        Returns number of coins
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ''
        text_to_search = f"{title_lower} {desc_lower}"
        
        patterns = [
            r'(\d+)\s*(?:coin|coins|pc|pcs|pieces)',
            r'lot\s+of\s+(\d+)',
            r'set\s+of\s+(\d+)',
            r'(\d+)\s*(?:x|count)',
            r'(\d+)\s*-\s*coin'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_to_search)
            for match in matches:
                try:
                    quantity = int(match)
                    if quantity > 0 and quantity <= 10000:  # Reasonable range
                        logger.debug(f"Extracted quantity: {quantity}")
                        return quantity
                except (ValueError, TypeError):
                    continue
        
        return 1
    
    def calculate_asw(self, item: Dict) -> Dict:
        """
        Calculate Actual Silver Weight for an eBay item
        Returns dict with ASW calculation details
        """
        title = item.get('title', '')
        description = item.get('description', '')
        
        result = {
            'identified': False,
            'coin_type': None,
            'coin_name': None,
            'asw': 0.0,
            'face_value': 0.0,
            'quantity': 1,
            'calculation_method': None,
            'confidence': 0.0
        }

        # Check for exclusion keywords first
        if self._is_excluded(title) or self._is_excluded(description):
            logger.debug(f"Item excluded (scam keywords): {title[:50]}...")
            return result
        
        # Try to identify coin type
        coin_info = self.identify_coin_type(title, description)
        
        if coin_info:
            result['identified'] = True
            result['coin_type'] = coin_info['type']
            result['coin_name'] = coin_info['name']
            result['calculation_method'] = 'pattern_match'
            result['confidence'] = 0.8
            
            # Handle junk silver (needs face value)
            if coin_info['type'] in ['junk silver', 'constitutional silver', '90% silver']:
                face_value = self.extract_face_value(title, description)
                if face_value > 0:
                    result['face_value'] = face_value
                    result['asw'] = coin_info['base_asw'] * face_value
                    result['confidence'] = 0.9
                else:
                    # Can't calculate ASW without face value
                    result['identified'] = False
                    logger.warning(f"Junk silver listing without face value: {title[:50]}")
            else:
                # Standard coins - check for quantity
                quantity = self.extract_quantity(title, description)
                result['quantity'] = quantity
                result['asw'] = coin_info['base_asw'] * quantity
                
                # Adjust confidence based on clarity
                if quantity > 1:
                    result['confidence'] = 0.7  # More uncertainty with quantities
                else:
                    result['confidence'] = 0.85
        
        return result
    
    def calculate_deal_metrics(self, item: Dict, asw_result: Dict, 
                              spot_price: float) -> Dict:
        """
        Calculate deal metrics for an item
        """
        total_cost = item.get('total_cost', 0.0)
        asw = asw_result.get('asw', 0.0)
        
        metrics = {
            'total_cost': total_cost,
            'asw': asw,
            'spot_price': spot_price,
            'cost_per_oz': 0.0,
            'discount_percent': 0.0,
            'is_deal': False,
            'threshold': spot_price * (Config.DEAL_THRESHOLD_PERCENTAGE / 100.0),
            'savings_per_oz': 0.0
        }
        
        if asw > 0 and total_cost > 0:
            metrics['cost_per_oz'] = total_cost / asw
            metrics['discount_percent'] = ((spot_price - metrics['cost_per_oz']) / spot_price) * 100
            metrics['savings_per_oz'] = spot_price - metrics['cost_per_oz']
            
            # Check if it's a deal
            if metrics['cost_per_oz'] <= metrics['threshold']:
                metrics['is_deal'] = True
            
            # Sanity check: reject obviously wrong calculations
            if metrics['cost_per_oz'] < 10:  # Too cheap to be real
                metrics['is_deal'] = False
                logger.warning(f"Suspiciously low cost per oz: ${metrics['cost_per_oz']:.2f}")
            elif metrics['cost_per_oz'] > 500:  # Too expensive
                metrics['is_deal'] = False
        
        return metrics
    
    def validate_deal(self, item: Dict, metrics: Dict) -> bool:
        """
        Validate if a deal meets all criteria
        """
        # Check discount threshold
        if not metrics['is_deal']:
            return False
        
        # Check seller feedback
        seller_feedback = item.get('seller_feedback', 0.0)
        if seller_feedback < Config.MIN_SELLER_FEEDBACK:
            logger.info(f"Rejected: Seller feedback {seller_feedback}% below minimum {Config.MIN_SELLER_FEEDBACK}%")
            return False
        
        # Check condition
        condition = item.get('condition', '').lower()
        if 'unknown' in condition or 'not specified' in condition:
            logger.info(f"Rejected: Unclear condition: {condition}")
            return False
        
        # Check shipping cost
        shipping_cost = item.get('shipping_cost', 0.0)
        if shipping_cost > Config.MAX_SHIPPING_COST:
            logger.info(f"Rejected: Shipping cost ${shipping_cost:.2f} exceeds maximum ${Config.MAX_SHIPPING_COST}")
            return False
        
        # Check if international seller (based on shipping)
        # This is a heuristic - in production you'd use actual seller location
        if shipping_cost > 25 and metrics['cost_per_oz'] < metrics['threshold'] * 0.9:
            logger.info(f"Rejected: Possible international seller with high shipping")
            return False
        
        return True