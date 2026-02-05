"""
Multi-Metal Spot Price Module
Fetches spot prices for gold, silver, platinum, and palladium
"""

import requests
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MultiMetalSpotPrice:
    """
    Fetch spot prices for multiple precious metals using CoinGecko API
    """
    
    def __init__(self):
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        
        # Mapping of our metal names to CoinGecko IDs
        self.metal_mapping = {
            'silver': 'silver',
            'gold': 'pax-gold',  # PAX Gold token tracks gold price accurately
            'platinum': 'platinum',
            'palladium': 'palladium'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Cache to avoid rate limiting
        self._cache = {}
        self._cache_duration = timedelta(minutes=5)
        self._last_request_time = 0
        self._min_request_interval = 2
    
    def get_spot_price(self, metal_type: str) -> Dict:
        """
        Get spot price for specified metal
        
        Args:
            metal_type: 'silver', 'gold', 'platinum', or 'palladium'
        
        Returns:
            Dict with spot_price, source, timestamp, verified
        """
        metal_type = metal_type.lower()
        
        if metal_type not in self.metal_mapping:
            raise ValueError(f"Unsupported metal type: {metal_type}")
        
        # Check cache first
        cache_key = f"single_{metal_type}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_duration:
                logger.debug(f"Using cached price for {metal_type}")
                return cached_data
        
        # Rate limiting
        self._rate_limit()
        
        try:
            coin_id = self.metal_mapping[metal_type]
            
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(self.coingecko_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if coin_id in data and 'usd' in data[coin_id]:
                price = data[coin_id]['usd']
                
                # Sanity checks for each metal
                if self._is_price_valid(metal_type, price):
                    logger.info(f"{metal_type.capitalize()} spot price from CoinGecko: ${price:.2f}/oz")
                    result = {
                        'spot_price': price,
                        'source': 'CoinGecko',
                        'timestamp': datetime.now().isoformat(),
                        'verified': True
                    }
                    # Cache the result
                    self._cache[cache_key] = (result, datetime.now())
                    return result
                else:
                    logger.warning(f"Price for {metal_type} outside expected range: ${price:.2f}")
            
        except Exception as e:
            logger.error(f"Error fetching {metal_type} spot price: {e}")
        
        return {
            'spot_price': None,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
    
    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def get_all_spot_prices(self) -> Dict[str, Dict]:
        """
        Get spot prices for all supported metals
        
        Returns:
            Dictionary with metal names as keys and price info as values
        """
        # Check cache first
        cache_key = "all_metals"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_duration:
                logger.debug("Using cached prices for all metals")
                return cached_data
        
        # Rate limiting
        self._rate_limit()
        
        try:
            # Get all metal IDs at once
            ids = ','.join(self.metal_mapping.values())
            
            params = {
                'ids': ids,
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(self.coingecko_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Process each metal
            results = {}
            for metal_name, coin_id in self.metal_mapping.items():
                if coin_id in data and 'usd' in data[coin_id]:
                    price = data[coin_id]['usd']
                    if self._is_price_valid(metal_name, price):
                        results[metal_name] = {
                            'spot_price': price,
                            'source': 'CoinGecko',
                            'timestamp': datetime.now().isoformat(),
                            'verified': True
                        }
                else:
                    results[metal_name] = {
                        'spot_price': None,
                        'source': 'None',
                        'timestamp': datetime.now().isoformat(),
                        'verified': False
                    }
            
            # Cache the results
            self._cache[cache_key] = (results, datetime.now())
            return results
            
        except Exception as e:
            logger.error(f"Error fetching all spot prices: {e}")
            return {metal: {'spot_price': None, 'source': 'None', 'verified': False} 
                    for metal in self.metal_mapping.keys()}
    
    def get_silver_price_info(self) -> Dict:
        """
        Get silver spot price with threshold calculation
        Returns dict with spot_price, threshold, source, timestamp
        """
        price_info = self.get_spot_price('silver')
        spot_price = price_info.get('spot_price')
        
        if spot_price:
            # Silver threshold: 83% of spot price (17% discount)
            threshold = spot_price * 0.83
            return {
                'spot_price': spot_price,
                'threshold': threshold,
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False)
            }
        
        return {
            'spot_price': None,
            'threshold': None,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
    
    def get_gold_price_info(self) -> Dict:
        """
        Get gold spot price with threshold calculation
        Returns dict with spot_price, threshold, source, timestamp
        """
        price_info = self.get_spot_price('gold')
        spot_price = price_info.get('spot_price')
        
        if spot_price:
            # Gold threshold: 85% of spot price (15% discount)
            threshold = spot_price * 0.85
            return {
                'spot_price': spot_price,
                'threshold': threshold,
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False)
            }
        
        return {
            'spot_price': None,
            'threshold': None,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
    
    def _is_price_valid(self, metal_type: str, price: float) -> bool:
        """
        Validate that price is within expected range for the metal
        
        Args:
            metal_type: Type of metal
            price: Price to validate
            
        Returns:
            True if price is valid, False otherwise
        """
        # Define reasonable price ranges for each metal (in USD per troy ounce)
        price_ranges = {
            'silver': (10, 100),      # Silver typically $15-$50
            'gold': (1000, 10000),    # Gold typically $1500-$3000
            'platinum': (500, 2000),  # Platinum typically $800-$1500
            'palladium': (500, 5000)  # Palladium typically $1000-$2500
        }
        
        if metal_type not in price_ranges:
            return False
        
        min_price, max_price = price_ranges[metal_type]
        return min_price <= price <= max_price