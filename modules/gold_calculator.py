"""
Gold Calculator Module
Intelligent pattern-based recognition for gold items
"""

import re
import logging
from typing import Dict, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)


class GoldCalculator:
    """
    Calculate Actual Gold Weight (AGW) for various gold items
    Uses intelligent pattern matching instead of hardcoded lists
    """
    
    def __init__(self):
        # AGW values for pre-1933 US gold coins
        self.pre_1933_agw = {
            '20': 0.9675,   # $20 Double Eagle
            '10': 0.48375,  # $10 Eagle
            '5': 0.24187,   # $5 Half Eagle
            '2.5': 0.12094, # $2.50 Quarter Eagle
            '2.50': 0.12094,
            '3': 0.14512,   # $3 Indian Princess
            '1': 0.04837,   # $1 Gold Dollar
        }
        
        # AGW for foreign gold coins
        self.foreign_agw = {
            'sovereign': 0.2354,  # British Sovereign
            'ducat': 0.1107,      # Austrian/Dutch Ducat
        }
        
        # Karat to purity conversion
        self.karat_purity = {
            10: 0.4167,
            14: 0.5833,
            18: 0.7500,
            22: 0.9167,
            24: 0.9999,
        }
        
        # Anti-scam exclusion keywords
        self.exclusion_keywords = [
            'plated', 'filled', 'overlay', 'tone', 'color',
            'replica', 'copy', 'fake', 'costume', 'fashion',
            'imitation', 'gold-colored', 'gold colored',
            'gold tone', 'gold-tone', 'not real gold',
            'not actual gold', 'gold appearance', 'looks like gold',
            'layered', 'vermeil', 'electroplate', 'gold leaf',
        ]
    
    def calculate_agw(self, item_details: Dict) -> Dict:
        """
        Calculate Actual Gold Weight from item details
        
        Returns:
            Dict with keys: identified, coin_type, coin_name, agw, 
                          purity, confidence, category
        """
        title = item_details.get('title', '').lower()
        
        # Check for exclusion keywords first
        if self._is_excluded(title):
            logger.debug(f"Item excluded (scam keywords): {title[:50]}...")
            return {'identified': False, 'reason': 'exclusion_keywords'}
        
        # Try to identify gold content through various methods
        result = None
        
        # 1. Try modern bullion coins
        result = self._identify_bullion_coin(title)
        if result['identified']:
            return result
        
        # 2. Try pre-1933 US gold coins
        result = self._identify_pre_1933(title)
        if result['identified']:
            return result
        
        # 3. Try foreign gold coins
        result = self._identify_foreign_coin(title)
        if result['identified']:
            return result
        
        # 4. Try gold bars and rounds
        result = self._identify_bar_or_round(title)
        if result['identified']:
            return result
        
        # 5. Try gold jewelry/scrap
        result = self._identify_jewelry(title)
        if result['identified']:
            return result
        
        # Not identified
        logger.debug(f"Could not identify gold content: {title[:50]}...")
        return {'identified': False, 'reason': 'no_pattern_match'}
    
    def _is_excluded(self, text: str) -> bool:
        """Check if text contains exclusion keywords"""
        return any(keyword in text for keyword in self.exclusion_keywords)
    
    def _identify_bullion_coin(self, text: str) -> Dict:
        """Identify modern bullion coins (Eagles, Buffalos, Maples, etc.)"""
        
        # Pattern: coin name + weight
        patterns = [
            # American Gold Eagle
            (r'(?:american\s+)?gold\s+eagle\s+(\d+(?:/\d+)?)\s*oz', 'American Gold Eagle'),
            (r'(\d+(?:/\d+)?)\s*oz\s+(?:american\s+)?gold\s+eagle', 'American Gold Eagle'),
            
            # Gold Buffalo
            (r'(?:american\s+)?gold\s+buffalo\s+(\d+(?:/\d+)?)\s*oz', 'American Gold Buffalo'),
            (r'(\d+(?:/\d+)?)\s*oz\s+gold\s+buffalo', 'American Gold Buffalo'),
            
            # Canadian Gold Maple Leaf
            (r'(?:canadian\s+)?(?:gold\s+)?maple\s+leaf\s+(\d+(?:/\d+)?)\s*oz', 'Canadian Gold Maple Leaf'),
            (r'(\d+(?:/\d+)?)\s*oz\s+(?:gold\s+)?maple', 'Canadian Gold Maple Leaf'),
            
            # Krugerrand
            (r'krugerrand\s+(\d+(?:/\d+)?)\s*oz', 'South African Krugerrand'),
            (r'(\d+(?:/\d+)?)\s*oz\s+krugerrand', 'South African Krugerrand'),
            
            # Austrian Philharmonic
            (r'(?:austrian\s+)?(?:gold\s+)?philharmonic\s+(\d+(?:/\d+)?)\s*oz', 'Austrian Philharmonic'),
            (r'(\d+(?:/\d+)?)\s*oz\s+philharmonic', 'Austrian Philharmonic'),
            
            # Britannia
            (r'(?:gold\s+)?britannia\s+(\d+(?:/\d+)?)\s*oz', 'British Britannia'),
            (r'(\d+(?:/\d+)?)\s*oz\s+britannia', 'British Britannia'),
            
            # Kangaroo/Nugget
            (r'(?:gold\s+)?(?:kangaroo|nugget)\s+(\d+(?:/\d+)?)\s*oz', 'Australian Kangaroo'),
            (r'(\d+(?:/\d+)?)\s*oz\s+(?:kangaroo|nugget)', 'Australian Kangaroo'),
            
            # Panda
            (r'(?:gold\s+)?panda\s+(\d+(?:/\d+)?)\s*oz', 'Chinese Gold Panda'),
            (r'(\d+(?:/\d+)?)\s*oz\s+(?:gold\s+)?panda', 'Chinese Gold Panda'),
        ]
        
        for pattern, coin_name in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                weight_str = match.group(1)
                agw = self._parse_weight_fraction(weight_str)
                
                if agw and agw >= 0.01:  # Minimum 0.01 oz
                    # Krugerrand is 22k, others are typically .9999
                    purity = 0.9167 if 'krugerrand' in text else 0.9999
                    
                    return {
                        'identified': True,
                        'coin_type': 'Modern Bullion',
                        'coin_name': coin_name,
                        'agw': agw,
                        'purity': purity,
                        'confidence': 0.95,
                        'category': 'bullion_coin'
                    }
        
        return {'identified': False}
    
    def _identify_pre_1933(self, text: str) -> Dict:
        """Identify pre-1933 US gold coins"""
        
        patterns = [
            # $20 Double Eagle
            (r'\$?\s*20\s+(?:dollar\s+)?(?:double\s+)?eagle', '20', '$20 Double Eagle'),
            (r'(?:double\s+)?eagle\s+\$?\s*20', '20', '$20 Double Eagle'),
            (r'saint\s+gaudens', '20', '$20 Saint-Gaudens'),
            (r'liberty\s+(?:head\s+)?\$?\s*20', '20', '$20 Liberty'),
            
            # $10 Eagle
            (r'\$?\s*10\s+(?:dollar\s+)?eagle', '10', '$10 Eagle'),
            (r'(?:liberty|indian)\s+(?:head\s+)?(?:eagle\s+)?\$?\s*10', '10', '$10 Eagle'),
            (r'\$?\s*10\s+(?:liberty|indian)', '10', '$10 Eagle'),
            
            # $5 Half Eagle
            (r'\$?\s*5\s+(?:dollar\s+)?(?:half\s+)?eagle', '5', '$5 Half Eagle'),
            (r'half\s+eagle\s+\$?\s*5', '5', '$5 Half Eagle'),
            (r'(?:liberty|indian)\s+(?:head\s+)?(?:eagle\s+)?\$?\s*5', '5', '$5 Half Eagle'),
            (r'\$?\s*5\s+(?:liberty|indian)', '5', '$5 Half Eagle'),
            
            # $2.50 Quarter Eagle
            (r'\$?\s*2\.?5?0?\s+(?:dollar\s+)?(?:quarter\s+)?eagle', '2.5', '$2.50 Quarter Eagle'),
            (r'quarter\s+eagle\s+\$?\s*2\.?5', '2.5', '$2.50 Quarter Eagle'),
            
            # $3 Indian Princess
            (r'\$?\s*3\s+(?:dollar\s+)?(?:indian|princess)', '3', '$3 Indian Princess'),
            
            # $1 Gold Dollar
            (r'\$?\s*1\s+(?:dollar\s+)?gold', '1', '$1 Gold Dollar'),
            (r'gold\s+dollar\s+\$?\s*1', '1', '$1 Gold Dollar'),
        ]
        
        for pattern, denomination, coin_name in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agw = self.pre_1933_agw.get(denomination, 0)
                
                if agw > 0:
                    return {
                        'identified': True,
                        'coin_type': 'Pre-1933 US Gold',
                        'coin_name': coin_name,
                        'agw': agw,
                        'purity': 0.9000,  # Pre-1933 coins are 90% gold
                        'confidence': 0.90,
                        'category': 'pre_1933'
                    }
        
        return {'identified': False}
    
    def _identify_foreign_coin(self, text: str) -> Dict:
        """Identify foreign gold coins"""
        
        patterns = [
            (r'\b(?:gold\s+)?sovereign\b', 'sovereign', 'British Gold Sovereign'),
            (r'\b(?:gold\s+)?ducat\b', 'ducat', 'Gold Ducat'),
        ]
        
        for pattern, key, coin_name in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agw = self.foreign_agw.get(key, 0)
                
                if agw > 0:
                    return {
                        'identified': True,
                        'coin_type': 'Foreign Gold Coin',
                        'coin_name': coin_name,
                        'agw': agw,
                        'purity': 0.9167,  # Most foreign coins are 22k
                        'confidence': 0.85,
                        'category': 'foreign_coin'
                    }
        
        return {'identified': False}
    
    def _identify_bar_or_round(self, text: str) -> Dict:
        """Identify gold bars and rounds"""
        
        # Try to extract weight and identify as bar/round
        weight_info = self._extract_weight(text)
        
        if not weight_info:
            return {'identified': False}
        
        weight_oz = weight_info['weight_oz']
        
        # Check if it's a bar or round
        is_bar = bool(re.search(r'\bgold\s+bar\b', text, re.IGNORECASE))
        is_round = bool(re.search(r'\bgold\s+round\b', text, re.IGNORECASE))
        
        if is_bar or is_round:
            item_type = 'Gold Bar' if is_bar else 'Gold Round'
            
            # Check for brand names
            brands = ['pamp', 'credit suisse', 'perth mint', 'valcambi', 
                     'johnson matthey', 'engelhard', 'sunshine']
            brand = next((b for b in brands if b in text), '')
            
            coin_name = f"{weight_info['display']} {brand} {item_type}".strip()
            
            return {
                'identified': True,
                'coin_type': item_type,
                'coin_name': coin_name,
                'agw': weight_oz,
                'purity': 0.9999,  # Bars/rounds typically .9999
                'confidence': 0.90,
                'category': 'bar_round'
            }
        
        return {'identified': False}
    
    def _identify_jewelry(self, text: str) -> Dict:
        """Identify gold jewelry/scrap"""
        
        # Look for karat + weight
        karat_match = re.search(r'(\d+)k(?:arat)?', text, re.IGNORECASE)
        
        if not karat_match:
            return {'identified': False}
        
        karat = int(karat_match.group(1))
        
        if karat not in self.karat_purity:
            return {'identified': False}
        
        # Extract weight
        weight_info = self._extract_weight(text)
        
        if not weight_info:
            # If no weight specified, we can't calculate AGW
            return {'identified': False}
        
        # Calculate AGW based on karat
        purity = self.karat_purity[karat]
        agw = weight_info['weight_oz'] * purity
        
        # Minimum AGW threshold for jewelry
        if agw < 0.01:  # Less than 0.01 oz is too small
            return {'identified': False}
        
        # Identify jewelry type
        jewelry_types = ['chain', 'bracelet', 'ring', 'necklace', 
                        'earring', 'pendant', 'watch', 'scrap']
        jewelry_type = next((jt for jt in jewelry_types if jt in text), 'jewelry')
        
        coin_name = f"{karat}k Gold {jewelry_type.title()} ({weight_info['display']})"
        
        return {
            'identified': True,
            'coin_type': f'{karat}k Gold Jewelry',
            'coin_name': coin_name,
            'agw': agw,
            'purity': purity,
            'confidence': 0.75,  # Lower confidence for jewelry
            'category': 'jewelry'
        }
    
    def _extract_weight(self, text: str) -> Optional[Dict]:
        """
        Extract weight from text
        Returns: Dict with weight_oz and display string, or None
        """
        
        # Try ounces (including fractions)
        oz_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?(?:oz|ounce)s?', 'decimal'),
            (r'(\d+)/(\d+)\s*oz', 'fraction'),
        ]
        
        for pattern, weight_type in oz_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if weight_type == 'decimal':
                    weight_oz = float(match.group(1))
                    display = f"{weight_oz} oz"
                else:  # fraction
                    numerator = int(match.group(1))
                    denominator = int(match.group(2))
                    weight_oz = numerator / denominator
                    display = f"{numerator}/{denominator} oz"
                
                return {'weight_oz': weight_oz, 'display': display}
        
        # Try grams
        gram_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:gram|g)s?', text, re.IGNORECASE)
        if gram_match:
            grams = float(gram_match.group(1))
            weight_oz = grams * 0.03215  # Convert grams to troy oz
            display = f"{grams}g"
            return {'weight_oz': weight_oz, 'display': display}
        
        # Try pennyweight (dwt)
        dwt_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:dwt|pennyweight)s?', text, re.IGNORECASE)
        if dwt_match:
            dwt = float(dwt_match.group(1))
            weight_oz = dwt * 0.05  # Convert dwt to troy oz
            display = f"{dwt} dwt"
            return {'weight_oz': weight_oz, 'display': display}
        
        # Try kilos
        kilo_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kilo|kg)s?', text, re.IGNORECASE)
        if kilo_match:
            kilos = float(kilo_match.group(1))
            weight_oz = kilos * 32.15  # Convert kg to troy oz
            display = f"{kilos} kg"
            return {'weight_oz': weight_oz, 'display': display}
        
        return None
    
    def _parse_weight_fraction(self, weight_str: str) -> Optional[float]:
        """Parse weight string that might be a fraction (e.g., '1/10')"""
        if '/' in weight_str:
            parts = weight_str.split('/')
            if len(parts) == 2:
                try:
                    return float(parts[0]) / float(parts[1])
                except (ValueError, ZeroDivisionError):
                    return None
        else:
            try:
                return float(weight_str)
            except ValueError:
                return None
        
        return None
    
    def calculate_deal_metrics(self, item: Dict, gold_result: Dict, spot_price: float) -> Dict:
        """
        Calculate deal metrics for a gold item
        
        Args:
            item: Item details dictionary
            gold_result: Gold calculation result from calculate_agw
            spot_price: Current spot price for gold
            
        Returns:
            Dictionary with deal metrics
        """
        total_cost = item.get('total_cost', 0.0)
        agw = gold_result.get('agw', 0.0)
        
        # Gold threshold: 85% of spot price (15% discount)
        threshold = spot_price * 0.85
        
        metrics = {
            'total_cost': total_cost,
            'agw': agw,
            'spot_price': spot_price,
            'cost_per_oz': 0.0,
            'discount_percent': 0.0,
            'is_deal': False,
            'threshold': threshold,
            'savings_per_oz': 0.0
        }
        
        if agw > 0 and total_cost > 0:
            metrics['cost_per_oz'] = total_cost / agw
            metrics['discount_percent'] = ((spot_price - metrics['cost_per_oz']) / spot_price) * 100
            metrics['savings_per_oz'] = spot_price - metrics['cost_per_oz']
            
            # Check if it's a deal
            if metrics['cost_per_oz'] <= metrics['threshold']:
                metrics['is_deal'] = True
            
            # Sanity checks for gold
            if metrics['cost_per_oz'] < 1000:  # Too cheap to be real gold
                metrics['is_deal'] = False
                logger.warning(f"Suspiciously low cost per oz for gold: ${metrics['cost_per_oz']:.2f}")
            elif metrics['cost_per_oz'] > 5000:  # Too expensive
                metrics['is_deal'] = False
        
        return metrics
    
    def validate_deal(self, item: Dict, metrics: Dict) -> bool:
        """
        Validate if a gold deal meets all criteria
        
        Args:
            item: Item details dictionary
            metrics: Deal metrics dictionary
            
        Returns:
            True if valid deal, False otherwise
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
        
        # Check price range (gold should be expensive enough)
        total_cost = item.get('total_cost', 0.0)
        if total_cost < 500:  # Too cheap for gold
            logger.info(f"Rejected: Price ${total_cost:.2f} too low for gold")
            return False
        
        return True
