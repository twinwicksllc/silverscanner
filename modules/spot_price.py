"""
Silver Spot Price Fetcher Module - Version 2
Two-Key Verification System with Fallback API
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Tuple
from config import Config
from database.models import DatabaseManager

logger = logging.getLogger(__name__)

class SilverSpotPrice:
    """Fetches and verifies silver spot prices using two-key verification"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.cache = {}
        self.cache_duration = timedelta(minutes=Config.SPOT_PRICE_CACHE_MINUTES)
        self.db_manager = db_manager or DatabaseManager()
        self.scrape_count = 0
        self.alpha_vantage_last_call = None  # Track when we last called Alpha Vantage
        self.alpha_vantage_cache_duration = timedelta(minutes=Config.ALPHA_VANTAGE_RATE_LIMIT_MINUTES)
        
    def get_spot_price(self, force_refresh: bool = False) -> Optional[float]:
        """
        Get current silver spot price using two-key verification
        
        Process:
        1. Fetch from both primary sources (JM Bullion, SD Bullion)
        2. If prices agree (within 5%), use average
        3. If prices disagree, fetch from fallback API to break tie
        4. Return verified price or None if verification fails
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh price
            
        Returns:
            Verified spot price per troy ounce in USD, or None if verification fails
        """
        # Check cache first (unless forced refresh)
        cache_key = 'spot_price'
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                logger.info(f"Using cached spot price: ${cached_data['price']:.2f}/oz")
                return cached_data['price']
        
        # Force refresh - bypass cache completely
        if force_refresh:
            logger.info("FORCE REFRESH: Bypassing cache and fetching fresh price")
        
        # Step 1: Fetch from primary sources
        logger.info("Fetching from primary sources (JM Bullion, SD Bullion)...")
        jm_price = self._fetch_from_jmbullion()
        sd_price = self._fetch_from_sdbullion()
        
        if not jm_price and not sd_price:
            logger.error("Failed to fetch from both primary sources")
            return None
        
        if not jm_price:
            logger.warning("JM Bullion failed, using SD Bullion only")
            return self._finalize_price(sd_price, "SD Bullion only")
        
        if not sd_price:
            logger.warning("SD Bullion failed, using JM Bullion only")
            return self._finalize_price(jm_price, "JM Bullion only")
        
        # Step 2: Calculate difference and verify
        avg_price = (jm_price + sd_price) / 2
        difference = abs(jm_price - sd_price)
        variance_threshold = Config.SPOT_PRICE_VARIANCE_THRESHOLD * avg_price
        
        logger.info(f"JM Bullion: ${jm_price:.2f}/oz")
        logger.info(f"SD Bullion: ${sd_price:.2f}/oz")
        logger.info(f"Difference: ${difference:.2f} (threshold: ${variance_threshold:.2f})")
        
        if difference <= variance_threshold:
            # Prices agree - use average
            logger.info(f"✓ Prices agree within {Config.SPOT_PRICE_VARIANCE_THRESHOLD*100}% threshold")
            return self._finalize_price(avg_price, "JM Bullion + SD Bullion (verified)")
        
        # Step 3: Prices disagree - use fallback to break tie
        logger.warning(f"⚠ Prices disagree by ${difference:.2f} (>{Config.SPOT_PRICE_VARIANCE_THRESHOLD*100}%)")
        logger.info("Fetching from fallback sources to break tie...")
        
        fallback_price = self._fetch_from_fallback()
        
        if not fallback_price:
            logger.warning("Fallback sources failed, using average of primary sources")
            return self._finalize_price(avg_price, "JM Bullion + SD Bullion (unverified)")
        
        # Determine which primary source is closer to fallback
        jm_diff = abs(jm_price - fallback_price)
        sd_diff = abs(sd_price - fallback_price)
        
        logger.info(f"Fallback price: ${fallback_price:.2f}/oz")
        logger.info(f"JM Bullion difference from fallback: ${jm_diff:.2f}")
        logger.info(f"SD Bullion difference from fallback: ${sd_diff:.2f}")
        
        if jm_diff < sd_diff:
            logger.info("✓ JM Bullion is closer to fallback - using JM Bullion")
            verified_price = jm_price
            source = "JM Bullion (verified by fallback)"
        else:
            logger.info("✓ SD Bullion is closer to fallback - using SD Bullion")
            verified_price = sd_price
            source = "SD Bullion (verified by fallback)"
        
        return self._finalize_price(verified_price, source)
    
    def _finalize_price(self, price: float, source: str) -> float:
        """Cache price, record to database, and return"""
        # Update cache
        self.cache['spot_price'] = {
            'price': price,
            'timestamp': datetime.now(),
            'source': source
        }
        
        logger.info(f"Final verified price: ${price:.2f}/oz from {source}")
        
        # Record price history (every fetch for immediate verification)
        self.scrape_count += 1
        self.db_manager.save_price_history(price, source)
        self.db_manager.cleanup_old_price_history(days=30)
        logger.info(f"💾 Price history recorded: ${price:.2f}/oz (source: {source})")
        
        return price
    
    def _fetch_from_jmbullion(self) -> Optional[float]:
        """Fetch spot price from JM Bullion - targets 'Live Spot Prices' section"""
        url = 'https://www.jmbullion.com/charts/silver-prices/'
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Strategy 1: Look for "Silver Ask" or "Silver:" in list items
            list_items = soup.find_all('li')
            for item in list_items:
                text = item.get_text()
                if 'Silver Ask' in text or 'Silver:' in text:
                    # Look for span with class "price" within this item
                    price_span = item.find('span', class_='price')
                    if price_span:
                        price_text = price_span.get_text().strip()
                        price = self._extract_price_from_text(price_text)
                        if price and 50 < price < 200:
                            logger.debug(f"JM Bullion: Found via 'Silver Ask' list item: ${price:.2f}")
                            return price
            
            # Strategy 2: Look for span.price with data-nosnippet near "Silver"
            price_spans = soup.find_all('span', class_='price', attrs={'data-nosnippet': True})
            for span in price_spans:
                # Check if this is in a silver-related context
                parent_text = span.parent.get_text() if span.parent else ''
                if 'Silver' in parent_text or 'silver' in parent_text.lower():
                    price_text = span.get_text().strip()
                    price = self._extract_price_from_text(price_text)
                    if price and 50 < price < 200:
                        logger.debug(f"JM Bullion: Found via data-nosnippet span: ${price:.2f}")
                        return price
            
            # Strategy 3: Look in spot-prices div/section
            spot_prices_div = soup.find('div', class_='spot-prices')
            if spot_prices_div:
                price_spans = spot_prices_div.find_all('span', class_='price')
                for span in price_spans:
                    # Check if this is the silver price (second one usually)
                    parent_text = span.parent.get_text() if span.parent else ''
                    if 'Silver' in parent_text:
                        price_text = span.get_text().strip()
                        price = self._extract_price_from_text(price_text)
                        if price and 50 < price < 200:
                            logger.debug(f"JM Bullion: Found in spot-prices div: ${price:.2f}")
                            return price
            
            logger.warning("JM Bullion: Could not find silver price in expected locations")
                    
        except Exception as e:
            logger.error(f"Error fetching from JM Bullion: {e}")
        
        return None
    
    def _fetch_from_sdbullion(self) -> Optional[float]:
        """Fetch spot price from SD Bullion"""
        url = 'https://sdbullion.com/silver-prices'
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for price elements
            price_elements = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'price' in x.lower())
            
            for element in price_elements:
                text = element.get_text().strip()
                price = self._extract_price_from_text(text)
                if price and 50 < price < 200:
                    return price
                    
        except Exception as e:
            logger.error(f"Error fetching from SD Bullion: {e}")
        
        return None
    
    def _fetch_from_fallback(self) -> Optional[float]:
        """
        Fetch from fallback sources to break tie
        Tries in order: Alpha Vantage (PRIMARY), Metals-API.com, APMEX scraping
        """
        # Try Alpha Vantage FIRST if API key is set (PRIMARY TIE-BREAKER)
        if Config.ALPHA_VANTAGE_API_KEY:
            price = self._fetch_from_alpha_vantage()
            if price:
                logger.info("✓ Using Alpha Vantage as tie-breaker")
                return price
        
        # Try Metals-API.com if API key is set
        if Config.METALS_API_KEY:
            price = self._fetch_from_metals_api()
            if price:
                logger.info("✓ Using Metals-API as tie-breaker")
                return price
        
        # Last resort: APMEX scraping (often returns 403)
        logger.warning("Attempting APMEX scraping as last resort...")
        return self._fetch_from_apmex()
    
    def _fetch_from_metals_api(self) -> Optional[float]:
        """Fetch from Metals-API.com (requires API key)"""
        try:
            url = f"https://metals-api.com/api/latest?access_key={Config.METALS_API_KEY}&base=USD&symbols=XAG"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success') and 'rates' in data and 'XAG' in data['rates']:
                # XAG is in troy ounces, rate is USD per ounce
                xag_rate = data['rates']['XAG']
                # Convert from XAG (ounces per USD) to USD per ounce
                price = 1 / xag_rate if xag_rate > 0 else None
                if price and 50 < price < 200:
                    logger.info(f"Metals-API price: ${price:.2f}/oz")
                    return price
                    
        except Exception as e:
            logger.error(f"Error fetching from Metals-API: {e}")
        
        return None
    
    def _fetch_from_alpha_vantage(self) -> Optional[float]:
        """Fetch from Alpha Vantage (requires API key, rate limited to 1x/hour)"""
        # Check rate limiting
        if self.alpha_vantage_last_call:
            time_since_last_call = datetime.now() - self.alpha_vantage_last_call
            if time_since_last_call < self.alpha_vantage_cache_duration:
                logger.warning(f"Alpha Vantage rate limited. Last call: {time_since_last_call.total_seconds()/60:.1f} minutes ago (min: {Config.ALPHA_VANTAGE_RATE_LIMIT_MINUTES} minutes)")
                return None
        
        try:
            logger.info("🔄 FETCHING FROM ALPHA VANTAGE (rate limited to 1x/hour)")
            url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAG&to_currency=USD&apikey={Config.ALPHA_VANTAGE_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                price = float(rate_data.get('5. Exchange Rate', 0))
                if price and 50 < price < 200:
                    logger.info(f"✅ Alpha Vantage price: ${price:.2f}/oz")
                    # Update last call timestamp
                    self.alpha_vantage_last_call = datetime.now()
                    return price
            else:
                logger.warning(f"Alpha Vantage response missing expected data: {data}")
                    
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
        
        return None
        
        return None
    
    def _fetch_from_apmex(self) -> Optional[float]:
        """Fetch spot price from APMEX (scraping fallback)"""
        url = 'https://www.apmex.com/spot/silver'
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # APMEX often has JSON data embedded
            import re
            json_pattern = r'"ask":\s*([\d.]+)'
            matches = re.findall(json_pattern, response.text)
            
            for match in matches:
                price = float(match)
                if 50 < price < 200:
                    logger.info(f"APMEX price: ${price:.2f}/oz")
                    return price
                    
        except Exception as e:
            logger.error(f"Error fetching from APMEX: {e}")
        
        return None
    
    def _extract_price_from_text(self, text: str) -> Optional[float]:
        """Extract price value from text"""
        import re
        
        # Remove currency symbols and extra whitespace
        text = text.replace('$', '').strip()
        
        # Look for price pattern
        price_pattern = r'(\d+\.\d{2})'
        matches = re.findall(price_pattern, text)
        
        if matches:
            return float(matches[0])
        
        return None
    
    def get_threshold(self) -> Optional[float]:
        """Calculate deal threshold based on spot price"""
        spot_price = self.get_spot_price()
        if spot_price:
            threshold = spot_price * (Config.DEAL_THRESHOLD_PERCENTAGE / 100.0)
            logger.info(f"Deal threshold: ${threshold:.2f}/oz ({Config.DEAL_THRESHOLD_PERCENTAGE}% of ${spot_price:.2f})")
            return threshold
        
        return None
    
    def get_price_info(self) -> Dict:
        """Get comprehensive price information"""
        spot_price = self.get_spot_price()
        threshold = self.get_threshold()
        
        return {
            'spot_price': spot_price,
            'threshold': threshold,
            'threshold_percentage': Config.DEAL_THRESHOLD_PERCENTAGE,
            'last_update': self.cache.get('spot_price', {}).get('timestamp'),
            'source': self.cache.get('spot_price', {}).get('source', 'Unknown')
        }