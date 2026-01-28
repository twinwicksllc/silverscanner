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
        # ALWAYS attempt live fetch first - cache is EMERGENCY FALLBACK ONLY
        # Step 1: Fetch from primary sources
        logger.info("Fetching from primary sources (JM Bullion, Kitco)...")
        jm_price = self._fetch_from_jmbullion()
        kitco_price = self._fetch_from_kitco()
        
        if not jm_price and not kitco_price:
            logger.error("Failed to fetch from both primary sources")
            # EMERGENCY FALLBACK: Use cache if available
            cache_key = 'spot_price'
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                logger.critical(f"⚠️ CRITICAL: All live sources failed. Using emergency cache: ${cached_data['price']:.2f}/oz (age: {(datetime.now() - cached_data['timestamp']).total_seconds()/60:.1f} minutes)")
                return cached_data['price']
            logger.critical("⚠️ CRITICAL: All live sources failed and no cache available!")
            return None
        
        if not jm_price:
            logger.warning("JM Bullion failed, using Kitco only")
            return self._finalize_price(kitco_price, "Kitco only")
        
        if not kitco_price:
            logger.warning("Kitco failed, using JM Bullion only")
            return self._finalize_price(jm_price, "JM Bullion only")
        
        # Step 2: Calculate difference and verify
        avg_price = (jm_price + kitco_price) / 2
        difference = abs(jm_price - kitco_price)
        variance_threshold = Config.SPOT_PRICE_VARIANCE_THRESHOLD * avg_price
        
        logger.info(f"JM Bullion: ${jm_price:.2f}/oz")
        logger.info(f"Kitco: ${kitco_price:.2f}/oz")
        logger.info(f"Difference: ${difference:.2f} (threshold: ${variance_threshold:.2f})")
        
        if difference <= variance_threshold:
            # Prices agree - use average
            logger.info(f"✓ Prices agree within {Config.SPOT_PRICE_VARIANCE_THRESHOLD*100}% threshold")
            return self._finalize_price(avg_price, "JM Bullion + Kitco (verified)")
        
        # Step 3: Prices disagree - use fallback to break tie
        logger.warning(f"⚠ Prices disagree by ${difference:.2f} (>{Config.SPOT_PRICE_VARIANCE_THRESHOLD*100}%)")
        logger.info("Fetching from fallback sources to break tie...")
        
        fallback_price = self._fetch_from_fallback()
        
        if not fallback_price:
            logger.critical("⚠️ CRITICAL: All fallback sources failed - using unverified average")
            logger.warning(f"Using average of JM Bullion (${jm_price:.2f}) and Kitco (${kitco_price:.2f})")
            return self._finalize_price(avg_price, "JM Bullion + Kitco (UNVERIFIED)")
        
        # Determine which primary source is closer to fallback
        jm_diff = abs(jm_price - fallback_price)
        kitco_diff = abs(kitco_price - fallback_price)
        
        logger.info(f"Fallback price: ${fallback_price:.2f}/oz")
        logger.info(f"JM Bullion difference from fallback: ${jm_diff:.2f}")
        logger.info(f"Kitco difference from fallback: ${kitco_diff:.2f}")
        
        if jm_diff < kitco_diff:
            logger.info("✓ JM Bullion is closer to fallback - using JM Bullion")
            verified_price = jm_price
            source = "JM Bullion (verified by fallback)"
        else:
            logger.info("✓ Kitco is closer to fallback - using Kitco")
            verified_price = kitco_price
            source = "Kitco (verified by fallback)"
        
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
        
        # Record price history every other scrape
        self.scrape_count += 1
        if self.scrape_count % 2 == 0:
            self.db_manager.save_price_history(price, source)
            self.db_manager.cleanup_old_price_history(days=30)
        
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
        """Fetch spot price from SD Bullion - uses direct silver-prices page"""
        url = 'https://sdbullion.com/silver-prices'
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Strategy 1: Look for the main spot price display at the top of the page
            # This should be the live current price, not historical data
            
            # Method 1: Look for large heading or prominent price display
            main_price_areas = soup.find_all(['h1', 'h2', 'div'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['spot', 'live', 'current', 'price', 'today']
            ))
            
            for area in main_price_areas[:5]:  # Check first 5 prominent areas
                text = area.get_text(strip=True)
                # Look for price in format $XXX.XX
                import re
                price_match = re.search(r'\$\s*([0-9]{2,3}\.[0-9]{2})', text)
                if price_match:
                    price = float(price_match.group(1))
                    if 50 < price < 200:
                        logger.info(f"SD Bullion price: ${price:.2f}/oz")
                        return price
            
            # Method 2: Look for structured data or meta tags
            meta_price = soup.find('meta', {'property': 'og:price:amount'})
            if meta_price:
                try:
                    price = float(meta_price.get('content', ''))
                    if 50 < price < 200:
                        logger.info(f"SD Bullion price (meta): ${price:.2f}/oz")
                        return price
                except (ValueError, TypeError):
                    pass
            
            # Method 3: Look for the first prominent price on the page (before historical table)
            # Get all text before "Historic" or "Historical" section
            page_text = soup.get_text()
            historical_index = page_text.lower().find('historic')
            if historical_index > 0:
                top_section = page_text[:historical_index]
            else:
                top_section = page_text[:2000]  # First 2000 chars
            
            import re
            price_pattern = r'\$\s*([0-9]{2,3}\.[0-9]{2})'
            matches = re.findall(price_pattern, top_section)
            
            for match in matches:
                price = float(match)
                if 50 < price < 200:
                    logger.info(f"SD Bullion price: ${price:.2f}/oz")
                    return price
                    
        except Exception as e:
            logger.error(f"Error fetching from SD Bullion: {e}")
        
        return None
    
    def _fetch_from_fallback(self) -> Optional[float]:
        """
        Fetch from fallback sources to break tie (100% FREE sources only)
        Tries in order: Alpha Vantage → Google Finance → SD Bullion
        """
        # Primary Fallback: Alpha Vantage (free API with rate limits)
        if Config.ALPHA_VANTAGE_API_KEY:
            price = self._fetch_from_alpha_vantage()
            if price:
                logger.info("✅ Using Alpha Vantage as fallback")
                return price
        
        # Secondary Fallback: Google Finance
        price = self._fetch_from_google()
        if price:
            logger.info("✅ Using Google Finance as fallback")
            return price
        
        # Tertiary Fallback: SD Bullion (may have stale data, but better than nothing)
        price = self._fetch_from_sdbullion()
        if price:
            logger.warning("⚠️ Using SD Bullion as fallback (may be stale)")
            return price
        
        # All fallback sources failed
        logger.critical("❌ CRITICAL: All fallback sources failed (Alpha Vantage, Google Finance, SD Bullion)")
        return None
    
    
    
    def _fetch_from_alpha_vantage(self) -> Optional[float]:
        """Fetch from Alpha Vantage (requires API key)"""
        try:
            url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAG&to_currency=USD&apikey={Config.ALPHA_VANTAGE_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                price = float(rate_data.get('5. Exchange Rate', 0))
                if price and 50 < price < 200:
                    logger.info(f"Alpha Vantage price: ${price:.2f}/oz")
                    return price
                    
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
        
        return None
    
    def _fetch_from_kitco(self) -> Optional[float]:
        """Fetch spot price from Kitco (reliable precious metals source)"""
        url = 'https://www.kitco.com/'
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
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Kitco displays spot prices in their header
            # Look for silver price in various locations
            silver_price = None
            
            # Method 1: Look for span with data-attribute
            price_elements = soup.find_all(['span', 'div'], {'data-symbol': 'silver', 'class': lambda x: x and ('price' in x.lower() or 'ask' in x.lower())})
            for elem in price_elements:
                text = elem.get_text(strip=True)
                price = self._extract_price_from_text(text)
                if price and 50 < price < 200:
                    silver_price = price
                    break
            
            # Method 2: Look for elements with text containing "Silver" and price
            if not silver_price:
                all_elements = soup.find_all(['span', 'div', 'td'])
                for elem in all_elements:
                    text = elem.get_text(strip=True)
                    if 'silver' in text.lower():
                        # Extract price from nearby text
                        price = self._extract_price_from_text(text)
                        if price and 50 < price < 200:
                            silver_price = price
                            break
            
            if silver_price:
                logger.info(f"Kitco price: ${silver_price:.2f}/oz")
                return silver_price
                
        except Exception as e:
            logger.error(f"Error fetching from Kitco: {e}")
        
        return None
    
    def _fetch_from_google(self) -> Optional[float]:
        """Fetch spot price from Google Finance SIW00 (silver spot)"""
        url = 'https://www.google.com/finance/quote/SIW00:COMEX'
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
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Google Finance displays the main price with class 'YMlKec fxKbKc'
            price_element = soup.find('div', class_='YMlKec fxKbKc')
            
            if price_element:
                text = price_element.get_text(strip=True)
                # Remove commas and currency symbols
                text = text.replace(',', '').replace('$', '')
                try:
                    price = float(text)
                    if 50 < price < 200:
                        logger.info(f"Google Finance (SIW00) spot price: ${price:.2f}/oz")
                        return price
                except ValueError:
                    pass
                    
        except Exception as e:
            logger.error(f"Error fetching from Google Finance: {e}")
        
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