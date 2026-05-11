"""
Multi-Metal Spot Price Module
Fetches spot prices for gold, silver, platinum, and palladium
"""

import requests
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)


class MultiMetalSpotPrice:
    """
    Fetch spot prices for multiple precious metals using CoinGecko API with fallback sources
    """
    
    def __init__(self):
        # Allow Config override for testing
        self.config = Config
        from database.models import DatabaseManager
        
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        
        # Mapping of our metal names to CoinGecko IDs
        self.metal_mapping = {
            'silver': 'silver',
            'gold': 'gold',  # Use actual gold, not pax-gold token
            'platinum': 'platinum',
            'palladium': 'palladium'
        }
        
        # Fallback scraping URLs for gold
        self.gold_fallback_urls = [
            'https://www.kitco.com/market/',
            'https://www.goldprice.org/',
            'https://www.monex.com/gold-prices/'
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Cache to avoid rate limiting
        self._cache = {}
        self._cache_duration = timedelta(minutes=5)
        self._last_request_time = 0
        self._min_request_interval = 2
        
        # Database manager for saving price history
        self.db_manager = DatabaseManager()
        
        # Last save time to avoid too frequent saves (at most once every 10 minutes)
        self._last_save_time = {'silver': None, 'gold': None, 'platinum': None, 'palladium': None}
        self.SAVE_INTERVAL_MINUTES = 10
    
    def _should_save_history(self, metal: str) -> bool:
        """Check if enough time has passed to save history again"""
        now = datetime.now()
        last_save = self._last_save_time.get(metal)
        
        if last_save is None:
            return True
            
        if now - last_save > timedelta(minutes=self.SAVE_INTERVAL_MINUTES):
            return True
            
        return False

    def _scrape_gold_price_kitco(self) -> Optional[float]:
        """Scrape gold price from Kitco as fallback"""
        try:
            response = self.session.get('https://www.kitco.com/market/', timeout=10)
            response.raise_for_status()
            
            # Look for gold price in the HTML - try multiple patterns
            import re
            
            # Pattern 1: Look for "Gold" followed by price
            patterns = [
                r'Gold[^$]*\$([0-9,]+\.[0-9]{2})',
                r'GOLD[^$]*\$([0-9,]+\.[0-9]{2})',
                r'XAU[^$]*\$([0-9,]+\.[0-9]{2})',
                r'gold-price[^>]*>.*?\$([0-9,]+\.[0-9]{2})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    try:
                        price_str = match.replace(',', '')
                        price = float(price_str)
                        if self._is_price_valid('gold', price):
                            logger.info(f"Scraped gold price from Kitco: ${price:.2f}/oz")
                            return price
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Failed to scrape Kitco: {e}")
        
        return None
    
    def _scrape_gold_price_goldprice_org(self) -> Optional[float]:
        """Scrape gold price from GoldPrice.org as fallback"""
        try:
            response = self.session.get('https://www.goldprice.org/', timeout=10)
            response.raise_for_status()
            
            # Look for gold price in specific elements
            import re
            
            # Try to find the main gold price display
            # GoldPrice.org typically shows: "Gold Price Per Ounce: $X,XXX.XX"
            patterns = [
                r'Gold Price Per Ounce[:\s]*\$([0-9,]+\.[0-9]{2})',
                r'gold-price[^>]*>.*?\$([0-9,]+\.[0-9]{2})',
                r'spot[^>]*gold[^>]*>.*?\$([0-9,]+\.[0-9]{2})',
                r'<span[^>]*gold[^>]*>.*?\$([0-9,]+\.[0-9]{2})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    try:
                        price = float(match.replace(',', ''))
                        if self._is_price_valid('gold', price):
                            logger.info(f"Scraped gold price from GoldPrice.org: ${price:.2f}/oz")
                            return price
                    except:
                        continue
        except Exception as e:
            logger.debug(f"Failed to scrape GoldPrice.org: {e}")
        
        return None
    
    def _get_gold_price_yahoo_finance(self) -> Optional[float]:
        """Get gold price from Yahoo Finance (GC=F ticker)"""
        try:
            # Yahoo Finance gold futures ticker
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/GC=F'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract current price from chart data
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    price = result['meta']['regularMarketPrice']
                    if self._is_price_valid('gold', price):
                        logger.info(f"Got gold price from Yahoo Finance: ${price:.2f}/oz")
                        return price
        except Exception as e:
            logger.debug(f"Failed to get Yahoo Finance gold price: {e}")
        
        return None
    
    def _get_silver_price_yahoo_finance(self) -> Optional[float]:
        """Get silver price from Yahoo Finance (SI=F ticker)"""
        try:
            # Yahoo Finance silver futures ticker
            url = 'https://query1.finance.yahoo.com/v8/finance/chart/SI=F'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract current price from chart data
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    price = result['meta']['regularMarketPrice']
                    if self._is_price_valid('silver', price):
                        logger.info(f"Got silver price from Yahoo Finance: ${price:.2f}/oz")
                        return price
        except Exception as e:
            logger.debug(f"Failed to get Yahoo Finance silver price: {e}")
        
        return None

    def _get_silver_price_with_fallback(self) -> Dict:
        """Get silver price with multiple fallback sources"""
        # Try CoinGecko first
        result = self.get_spot_price('silver')
        if result.get('spot_price'):
            return result
        
        logger.warning("CoinGecko silver price unavailable, trying fallback sources...")
        
        # Try Yahoo Finance (most reliable)
        price = self._get_silver_price_yahoo_finance()
        if price:
            return {
                'spot_price': price,
                'source': 'Yahoo Finance',
                'timestamp': datetime.now().isoformat(),
                'verified': True
            }
        
        logger.error("All silver price sources failed")
        return {
            'spot_price': None,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }

    def _get_gold_price_with_fallback(self) -> Dict:
        """Get gold price with multiple fallback sources"""
        # Try CoinGecko first
        result = self.get_spot_price('gold')
        if result.get('spot_price'):
            return result
        
        logger.warning("CoinGecko gold price unavailable, trying fallback sources...")
        
        # Try Yahoo Finance (most reliable)
        price = self._get_gold_price_yahoo_finance()
        if price:
            return {
                'spot_price': price,
                'source': 'Yahoo Finance',
                'timestamp': datetime.now().isoformat(),
                'verified': True
            }
        
        # Try Kitco
        price = self._scrape_gold_price_kitco()
        if price:
            return {
                'spot_price': price,
                'source': 'Kitco (scraped)',
                'timestamp': datetime.now().isoformat(),
                'verified': True
            }
        
        # Try GoldPrice.org
        price = self._scrape_gold_price_goldprice_org()
        if price:
            return {
                'spot_price': price,
                'source': 'GoldPrice.org (scraped)',
                'timestamp': datetime.now().isoformat(),
                'verified': True
            }
        
        logger.error("All gold price sources failed")
        return {
            'spot_price': None,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
    
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
                        
                        # Save price history if interval reached
                        if self._should_save_history(metal_name):
                            try:
                                self.db_manager.save_price_history(
                                    price=price,
                                    source='CoinGecko',
                                    metal_type=metal_name
                                )
                                self._last_save_time[metal_name] = datetime.now()
                            except Exception as db_err:
                                logger.error(f"Error saving {metal_name} price history: {db_err}")
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
        Uses fallback sources if CoinGecko fails
        Returns dict with spot_price, threshold, source, timestamp
        """
        price_info = self._get_silver_price_with_fallback()
        spot_price = price_info.get('spot_price')
        
        if spot_price:
            # Silver threshold: Use configured threshold
            threshold_percent = Config.DEAL_THRESHOLD_PERCENTAGE / 100.0
            threshold = spot_price * threshold_percent
            
            price_info['threshold'] = threshold
            price_info['threshold_percentage'] = Config.DEAL_THRESHOLD_PERCENTAGE
            
            # Save price history if interval reached
            if self._should_save_history('silver'):
                self.db_manager.save_price_history(
                    price=spot_price,
                    source=price_info.get('source'),
                    metal_type='silver'
                )
                self._last_save_time['silver'] = datetime.now()
            
            return {
                'spot_price': spot_price,
                'threshold': threshold,
                'threshold_percentage': price_info.get('threshold_percentage', Config.DEAL_THRESHOLD_PERCENTAGE),
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False)
            }
        
        return {
            'spot_price': None,
            'threshold': None,
            'threshold_percentage': Config.DEAL_THRESHOLD_PERCENTAGE,
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
    
    def get_gold_price_info(self) -> Dict:
        """
        Get gold spot price with threshold calculation
        Uses fallback sources if CoinGecko fails
        Returns dict with spot_price, threshold, source, timestamp
        """
        price_info = self._get_gold_price_with_fallback()
        spot_price = price_info.get('spot_price')
        
        if spot_price:
            # Gold threshold: 85% of spot price (15% discount)
            # Default to 92% if setting missing
            threshold_percent = Config.METAL_THRESHOLDS.get('gold', 92.0) / 100.0
            threshold = spot_price * threshold_percent
            
            price_info['threshold'] = threshold
            price_info['threshold_percentage'] = Config.METAL_THRESHOLDS.get('gold', 92.0)
            
            # Save price history if interval reached
            if self._should_save_history('gold'):
                self.db_manager.save_price_history(
                    price=spot_price,
                    source=price_info.get('source'),
                    metal_type='gold'
                )
                self._last_save_time['gold'] = datetime.now()
            
            return {
                'spot_price': spot_price,
                'threshold': threshold,
                'threshold_percentage': price_info.get('threshold_percentage', Config.METAL_THRESHOLDS.get('gold', 92.0)),
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False)
            }
        
        return {
            'spot_price': None,
            'threshold': None,
            'threshold_percentage': Config.METAL_THRESHOLDS.get('gold', 92.0),
            'source': 'None',
            'timestamp': datetime.now().isoformat(),
            'verified': False
        }
                    price=spot_price,
                    source=price_info.get('source'),
                    metal_type='gold'
                )
            
            return {
                'spot_price': spot_price,
                'threshold': threshold,
                'threshold_percentage': price_info.get('threshold_percentage', Config.METAL_THRESHOLDS.get('gold', 92.0)),
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False)
            }
        
        return {
            'spot_price': None,
            'threshold': None,
            'threshold_percentage': Config.METAL_THRESHOLDS.get('gold', 92.0),
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