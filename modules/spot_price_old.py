"""
Silver Spot Price Fetcher Module
Retrieves current silver spot prices from multiple sources
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict
from config import Config
from database.models import DatabaseManager

logger = logging.getLogger(__name__)

class SilverSpotPrice:
    
    """Fetches and caches silver spot prices from multiple sources"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.cache = {}
        self.cache_duration = timedelta(minutes=Config.SPOT_PRICE_CACHE_MINUTES)
        self.db_manager = db_manager or DatabaseManager()
        self.scrape_count = 0  # Track number of scrapes to record every other one
        
    def get_spot_price(self, force_refresh: bool = False) -> Optional[float]:
        """
        Get current silver spot price from cache or fetch from sources
        Averages prices from multiple sources for accuracy
        Returns price per troy ounce in USD
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh price
        """
        # Check cache first (unless forced refresh)
        cache_key = 'spot_price'
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                logger.info(f"Using cached spot price: ${cached_data['price']:.2f}/oz")
                return cached_data['price']
        
        # Fetch prices from all sources
        prices = []
        sources_used = []
        
        for source_url in Config.SPOT_PRICE_SOURCES:
            try:
                price = self._fetch_from_source(source_url)
                if price and price > 0:
                    prices.append(price)
                    sources_used.append(source_url)
                    logger.info(f"Fetched ${price:.2f}/oz from {source_url}")
            except Exception as e:
                logger.warning(f"Failed to fetch from {source_url}: {e}")
                continue
        
        # Calculate average if we got at least one price
        if prices:
            avg_price = sum(prices) / len(prices)
            
            # Update cache
            self.cache[cache_key] = {
                'price': avg_price,
                'timestamp': datetime.now(),
                'source': ', '.join(sources_used),
                'individual_prices': prices
            }
            
            logger.info(f"Averaged spot price: ${avg_price:.2f}/oz from {len(prices)} source(s)")
            if len(prices) > 1:
                logger.info(f"Individual prices: {', '.join([f'${p:.2f}' for p in prices])}")
            
            # Record price history every other scrape
            self.scrape_count += 1
            if self.scrape_count % 2 == 0:
                self.db_manager.save_price_history(avg_price, f"Average of {len(prices)} sources")
                # Clean up old records (older than 1 month)
                self.db_manager.cleanup_old_price_history(days=30)
            
            return avg_price
        
        logger.error("Failed to fetch spot price from all sources")
        return None
    
    def _fetch_from_source(self, url: str) -> Optional[float]:
        """
        Fetch spot price from a specific source
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            if 'jmbullion' in url:
                return self._parse_jmbullion(response.text)
            elif 'sdbullion' in url:
                return self._parse_sdbullion(response.text)
            elif 'apmex' in url:
                return self._parse_apmex(response.text)
            else:
                logger.warning(f"Unknown source: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching from {url}: {e}")
            return None
    
    def _parse_jmbullion(self, html: str) -> Optional[float]:
        """Parse spot price from JM Bullion"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple selectors for JM Bullion
            selectors = [
                'span.price',
                'div.price',
                '.spot-price',
                'p.price',
                '[data-price]'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text().strip()
                    # Extract price from text like "$108.43" or "108.43"
                    price = self._extract_price_from_text(text)
                    if price and price > 50 and price < 200:  # Reasonable range for silver
                        return price
            
            # Fallback: Look for price pattern in page text
            import re
            price_pattern = r'\$(\d+\.\d{2})'
            matches = re.findall(price_pattern, html)
            for match in matches:
                price = float(match)
                if price > 50 and price < 200:
                    return price
                    
        except Exception as e:
            logger.error(f"Error parsing JM Bullion: {e}")
        
        return None
    
    def _parse_sdbullion(self, html: str) -> Optional[float]:
        """Parse spot price from SD Bullion"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for price elements
            price_elements = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'price' in x.lower())
            
            for element in price_elements:
                text = element.get_text().strip()
                price = self._extract_price_from_text(text)
                if price and price > 50 and price < 200:
                    return price
                    
        except Exception as e:
            logger.error(f"Error parsing SD Bullion: {e}")
        
        return None
    
    def _parse_apmex(self, html: str) -> Optional[float]:
        """Parse spot price from APMEX"""
        try:
            # APMEX often has JSON data embedded
            import re
            json_pattern = r'"ask":\s*([\d.]+)'
            matches = re.findall(json_pattern, html)
            
            for match in matches:
                price = float(match)
                if price > 50 and price < 200:
                    return price
                    
        except Exception as e:
            logger.error(f"Error parsing APMEX: {e}")
        
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
        """
        Calculate deal threshold (83% of spot price)
        """
        spot_price = self.get_spot_price()
        if spot_price:
            threshold = spot_price * (Config.DEAL_THRESHOLD_PERCENTAGE / 100.0)
            logger.info(f"Deal threshold: ${threshold:.2f}/oz (83% of ${spot_price:.2f})")
            return threshold
        
        return None
    
    def get_price_info(self) -> Dict:
        """
        Get comprehensive price information
        Returns dict with spot price, threshold, and metadata
        """
        spot_price = self.get_spot_price()
        threshold = self.get_threshold()
        
        return {
            'spot_price': spot_price,
            'threshold': threshold,
            'threshold_percentage': Config.DEAL_THRESHOLD_PERCENTAGE,
            'last_update': self.cache.get('spot_price', {}).get('timestamp'),
            'source': self.cache.get('spot_price', {}).get('source', 'Unknown')
        }