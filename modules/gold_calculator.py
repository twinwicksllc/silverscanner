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
        
        # Skip items that are clearly SILVER (not gold)
        silver_keywords = ['silver krugerrand', 'silver eagle', 'silver maple', 
                          'silver buffalo', 'silver philharmonic', 'silver britannia',
                          'silver panda', 'silver kangaroo', 'silver koala',
                          '1 oz silver', '1oz silver', 'troy oz silver', 
                          'silver bar', 'silver round', 'silver coin',
                          ' 999 silver', '.999 silver', 'pure silver']
        if any(kw in title for kw in silver_keywords):
            logger.debug(f"Item is silver (not gold): {title[:50]}...")
            return {'identified': False, 'reason': 'silver_item'}
        
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
        return {'identified': False, 'reason': 'no_pattern_match'}

    def _is_excluded(self, text: str) -> bool:
        """Check if item contains exclusion keywords"""
        return any(kw in text for kw in self.exclusion_keywords)

    def _identify_bullion_coin(self, text: str) -> Dict:
        """Identify modern bullion coins"""
        
        patterns = [
            # American Gold Eagle (modern bullion)
            (r'(?:american\s+)?gold\s+eagle\s+1\s*(?:oz|troy)', '1oz_gold_eagle', 'American Gold Eagle 1 oz', 1.0),
            (r'1\s*(?:oz|troy).*gold\s+eagle', '1oz_gold_eagle', 'American Gold Eagle 1 oz', 1.0),
            (r'(?:american\s+)?gold\s+eagle\s+(?:1/2|half)\s*oz', '0.5oz_gold_eagle', 'American Gold Eagle 1/2 oz', 0.5),
            (r'(?:american\s+)?gold\s+eagle\s+(?:1/4|quarter)\s*oz', '0.25oz_gold_eagle', 'American Gold Eagle 1/4 oz', 0.25),
            (r'(?:american\s+)?gold\s+eagle\s+(?:1/10|tenth)\s*oz', '0.1oz_gold_eagle', 'American Gold Eagle 1/10 oz', 0.1),
            
            # Gold Buffalo
            (r'(?:american\s+)?gold\s+buffalo\s+1\s*(?:oz|troy)', '1oz_gold_buffalo', 'American Gold Buffalo 1 oz', 1.0),
            (r'1\s*(?:oz|troy).*gold\s+buffalo', '1oz_gold_buffalo', 'American Gold Buffalo 1 oz', 1.0),
            
            # Canadian Gold Maple
            (r'(?:canadian\s+)?gold\s+maple(?:\s+leaf)?\s+1\s*(?:oz|troy)', '1oz_maple', 'Canadian Gold Maple Leaf 1 oz', 1.0),
            (r'1\s*(?:oz|troy).*(?:gold\s+maple|maple.*gold)', '1oz_maple', 'Canadian Gold Maple Leaf 1 oz', 1.0),
            
            # South African Gold Krugerrand (must exclude SILVER Krugerrand)
            (r'gold\s+krugerrand\s+1\s*(?:oz|troy)', '1oz_krugerrand', 'Gold Krugerrand 1 oz', 1.0),
            (r'1\s*(?:oz|troy)\s*gold\s*krugerrand', '1oz_krugerrand', 'Gold Krugerrand 1 oz', 1.0),
            (r'krugerrand\s+1\s*(?:oz|troy)\s*gold', '1oz_krugerrand', 'Gold Krugerrand 1 oz', 1.0),
            # Krugerrand without explicit "silver" keyword (default is gold)
            (r'(?<!silver\s)krugerrand\s+1\s*(?:oz|troy)(?!\s*silver)', '1oz_krugerrand', 'Gold Krugerrand 1 oz', 1.0),
            
            # Austrian Philharmonic
            (r'(?:austrian\s+)?(?:gold\s+)?philharmonic', '1oz_philharmonic', 'Austrian Gold Philharmonic 1 oz', 1.0),
        ]
        
        for pattern, coin_type, coin_name, agw in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'identified': True,
                    'coin_type': coin_type,
                    'coin_name': coin_name,
                    'agw': agw,
                    'purity': 0.9999,
                    'confidence': 0.90,
                    'category': 'bullion_coin'
                }
        
        return {'identified': False}

    def _identify_pre_1933(self, text: str) -> Dict:
        """Identify pre-1933 US gold coins"""
        
        # IMPORTANT: Patterns are ordered from most specific to most generic
        # to avoid false matches. Quarter Eagle and Half Eagle must come before
        # generic "gold eagle" patterns.
        patterns = [
            # ── $2.50 Quarter Eagle (MOST SPECIFIC FIRST) ──────────────────
            # Explicit denomination
            (r'\$\s*2\.50\s+(?:quarter\s+)?eagle', '2.5', '$2.50 Quarter Eagle'),
            (r'\$\s*2\.5\s+(?:quarter\s+)?eagle', '2.5', '$2.50 Quarter Eagle'),
            (r'quarter\s+eagle\s+\$?\s*2\.?5', '2.5', '$2.50 Quarter Eagle'),
            # "Quarter Eagle" keyword (no denomination needed - unambiguous)
            (r'quarter\s+eagle', '2.5', '$2.50 Quarter Eagle'),
            # "Indian/Liberty Head Gold Quarter Eagle"
            (r'(?:indian|liberty)\s+head\s+gold\s+quarter\s+eagle', '2.5', '$2.50 Quarter Eagle'),
            (r'\bS\s*2\.?5\b.*(?:eagle|gold)', '2.5', '$2.50 Quarter Eagle'),

            # ── $5 Half Eagle ───────────────────────────────────────────────
            # Explicit denomination
            (r'\$\s*5\s+(?:half\s+)?eagle', '5', '$5 Half Eagle'),
            (r'half\s+eagle\s+\$?\s*5', '5', '$5 Half Eagle'),
            (r'\bS\s*5\b.*(?:eagle|gold)', '5', '$5 Half Eagle'),
            # "Half Eagle" keyword (unambiguous)
            (r'half\s+eagle', '5', '$5 Half Eagle'),
            # "Indian/Liberty Head $5"
            (r'(?:liberty|indian)\s+(?:head\s+)?\$\s*5', '5', '$5 Half Eagle'),
            (r'\$\s*5\s+(?:liberty|indian)', '5', '$5 Half Eagle'),

            # ── $10 Eagle ───────────────────────────────────────────────────
            # Explicit denomination (must come before generic "gold eagle")
            (r'\$\s*10\s+(?:liberty|indian|eagle|gold)', '10', '$10 Eagle'),
            (r'(?:liberty|indian)\s+(?:head\s+)?\$\s*10', '10', '$10 Eagle'),
            (r'(?:liberty|indian)\s+head\s+gold\s+eagle.*\$?\s*10\b', '10', '$10 Eagle'),
            (r'\$?\s*10.*(?:liberty|indian)\s+head\s+gold\s+eagle', '10', '$10 Eagle'),
            (r'\bS\s*10\b.*(?:eagle|gold)', '10', '$10 Eagle'),
            (r'\$?\s*10\s+(?:dollar\s+)?eagle', '10', '$10 Eagle'),

            # ── $20 Double Eagle ────────────────────────────────────────────
            # Explicit denomination
            (r'\$?\s*20\s+(?:dollar\s+)?(?:double\s+)?eagle', '20', '$20 Double Eagle'),
            (r'(?:double\s+)?eagle\s+\$?\s*20', '20', '$20 Double Eagle'),
            (r'saint\s+gaudens', '20', '$20 Saint-Gaudens'),
            (r'liberty\s+(?:head\s+)?\$?\s*20', '20', '$20 Liberty'),
            # "S20" denomination format used in some eBay titles (not quarter eagle)
            (r'\bS\s*20\b', '20', '$20 Double Eagle'),
            # Generic "liberty head gold eagle" or "MS liberty head gold eagle"
            # (no other denomination found = assume $20 Double Eagle, the most common)
            (r'liberty\s+head\s+gold\s+eagle', '20', '$20 Liberty Head Gold Eagle'),

            # ── $3 Indian Princess ──────────────────────────────────────────
            (r'\$?\s*3\s+(?:dollar\s+)?(?:indian|princess)', '3', '$3 Indian Princess'),

            # ── $1 Gold Dollar ──────────────────────────────────────────────
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
        
        # Check for "gold bar" or "gold round" keywords first
        is_bar = bool(re.search(r'\b(?:gold\s+)?bar\b', text, re.IGNORECASE)) and 'gold' in text
        is_round = bool(re.search(r'\bgold\s+round\b', text, re.IGNORECASE))
        
        # Also check for collectible bars with gold content (e.g., "1/4 grain 24k gold bar")
        has_gold_bar = bool(re.search(r'\d+(?:/\d+)?\s*grain.*(?:\d+k\s+)?gold', text, re.IGNORECASE))
        has_gold_bar = has_gold_bar or bool(re.search(r'\d+k\s+gold\s+bar', text, re.IGNORECASE))
        
        if not (is_bar or is_round or has_gold_bar):
            return {'identified': False}
        
        # Try to extract weight
        weight_info = self._extract_weight(text)
        
        if not weight_info:
            return {'identified': False}
        
        weight_oz = weight_info['weight_oz']
        
        # Extract karat if present (e.g., "24k gold bar")
        karat_match = re.search(r'(\d+)k\s+(?:gold\s+)?bar', text, re.IGNORECASE)
        if karat_match:
            karat = int(karat_match.group(1))
            purity = self.karat_purity.get(karat, 0.9999)
        else:
            purity = 0.9999
        
        item_type = 'Gold Bar' if (is_bar or has_gold_bar) else 'Gold Round'
        
        return {
            'identified': True,
            'coin_type': f'{weight_oz:.6f}oz_gold_{"bar" if (is_bar or has_gold_bar) else "round"}',
            'coin_name': f'{weight_oz:.6f} oz {item_type}',
            'agw': weight_oz * purity,  # AGW accounts for purity
            'purity': purity,
            'confidence': 0.85,
            'category': 'bar_round'
        }

    def _identify_jewelry(self, text: str) -> Dict:
        """Identify gold jewelry/scrap by karat and weight"""
        
        # Must contain gold indicator
        if not re.search(r'\bgold\b', text, re.IGNORECASE):
            return {'identified': False}
        
        # Extract karat
        karat = self._extract_karat(text)
        if not karat:
            return {'identified': False}
        
        purity = self.karat_purity.get(karat, 0)
        if not purity:
            return {'identified': False}
        
        # Extract weight
        weight_info = self._extract_weight(text)
        if not weight_info:
            return {'identified': False}
        
        weight_oz = weight_info['weight_oz']
        agw = weight_oz * purity
        
        return {
            'identified': True,
            'coin_type': f'{karat}k_gold_jewelry',
            'coin_name': f'{karat}k Gold ({weight_oz:.3f} oz)',
            'agw': round(agw, 4),
            'purity': purity,
            'confidence': 0.75,
            'category': 'jewelry'
        }

    def _extract_karat(self, text: str) -> Optional[int]:
        """Extract gold karat from text"""
        patterns = [
            r'(\d+)\s*(?:k|kt|karat|carat)\s*(?:gold|au)?',
            r'(?:gold|au)\s*(\d+)\s*(?:k|kt|karat|carat)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    karat = int(match.group(1))
                    if karat in self.karat_purity:
                        return karat
                except (ValueError, IndexError):
                    pass
        return None

    def _extract_weight(self, text: str) -> Optional[Dict]:
        """Extract weight from text, converting to troy oz"""
        
        # IMPORTANT: Check for GRAIN first - it's a tiny unit often confused with gram
        # 1 grain = 0.002083 troy oz (NOT the same as gram!)
        grain_match = re.search(r'(\d+(?:/\d+)?)\s*grain', text, re.IGNORECASE)
        if grain_match:
            try:
                weight_str = grain_match.group(1)
                if '/' in weight_str:
                    # Fraction like "1/4 grain"
                    num, denom = weight_str.split('/')
                    weight = float(num) / float(denom)
                else:
                    weight = float(weight_str)
                # 1 grain = 0.002083 troy oz
                return {
                    'weight': weight,
                    'unit': 'grain',
                    'weight_oz': weight * 0.002083
                }
            except (ValueError, ZeroDivisionError):
                pass
        
        patterns = [
            # Troy oz
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?oz(?:s|troy)?', 'troy_oz', 1.0),
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?ounce', 'troy_oz', 1.0),
            # Grams (must NOT match "grain" - use word boundary)
            (r'(\d+(?:\.\d+)?)\s*g\b(?!rain)', 'grams', 1/31.1035),
            (r'(\d+(?:\.\d+)?)\s*grams?', 'grams', 1/31.1035),
            # Pennyweight
            (r'(\d+(?:\.\d+)?)\s*(?:dwt|pennyweight)', 'dwt', 1/20.0),
        ]
        
        for pattern, unit, conversion in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    weight = float(match.group(1))
                    if 0.001 < weight < 1000:  # Sanity check
                        return {
                            'weight': weight,
                            'unit': unit,
                            'weight_oz': weight * conversion
                        }
                except (ValueError, IndexError):
                    pass
        
        return None

    def calculate_deal_metrics(self, item: Dict, agw_result: Dict, spot_price: float) -> Dict:
        """Calculate deal metrics for a gold item"""
        
        total_cost = item.get('total_cost', 0.0)
        agw = agw_result.get('agw', 0.0)
        
        metrics = {
            'total_cost': total_cost,
            'agw': agw,
            'spot_price': spot_price,
            'cost_per_oz': 0.0,
            'discount_percent': 0.0,
            'is_deal': False,
            'savings_per_oz': 0.0
        }
        
        if agw > 0 and total_cost > 0:
            metrics['cost_per_oz'] = total_cost / agw
            metrics['discount_percent'] = ((spot_price - metrics['cost_per_oz']) / spot_price) * 100
            metrics['savings_per_oz'] = spot_price - metrics['cost_per_oz']
            
            # Check if it's a deal (below spot)
            if metrics['cost_per_oz'] <= spot_price * (Config.DEAL_THRESHOLD_PERCENTAGE / 100.0):
                metrics['is_deal'] = True
        
        return metrics