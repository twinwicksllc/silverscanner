"""
eBay API Client Module
Handles authentication and data retrieval from eBay Browse API
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class eBayAPI:
    """eBay Browse API client with OAuth authentication"""
    
    def __init__(self):
        self.access_token = None
        self.token_expiry = None
        self.headers = {
            'Content-Type': 'application/json',
            'X-EBAY-C-MARKETPLACE-ID': Config.EBAY_MARKETPLACE_ID
        }
        
    def authenticate(self) -> bool:
        """
        Obtain OAuth 2.0 access token using client credentials flow
        """
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            logger.info("Using existing valid access token")
            return True
        
        try:
            auth_url = Config.EBAY_OAUTH_URL
            credentials = (Config.EBAY_CLIENT_ID, Config.EBAY_CLIENT_SECRET)
            data = {
                'grant_type': 'client_credentials',
                'scope': 'https://api.ebay.com/oauth/api_scope'
            }
            
            logger.info("Authenticating with eBay API...")
            response = requests.post(auth_url, auth=credentials, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
            
            # Set expiry with 5-minute buffer
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            
            self.headers['Authorization'] = f'Bearer {self.access_token}'
            logger.info("Successfully obtained eBay API access token")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"eBay API authentication failed: {e}")
            return False
    
    def search_listings(self, keywords: str, category_id: str = None, 
                       max_results: int = 100) -> List[Dict]:
        """
        Search eBay listings with specific filters
        """
        if not self.authenticate():
            logger.error("Cannot search: authentication failed")
            return []
        
        try:
            # Build search URL
            search_url = f"{Config.EBAY_API_BASE_URL}/item_summary/search"
            
            # Build query parameters
            params = {
                'q': keywords,
                'limit': min(max_results, 100),  # API max is 100
                'filter': 'buyingOptions:{FIXED_PRICE}',
                'fieldgroups': 'EXTENDED'
            }
            
            # Add category filter if specified
            if category_id:
                params['filter'] += f',categoryIds:{category_id}'
            
            # Add shipping filter to exclude items with no shipping
            params['filter'] += ',deliveryCountry:US'
            
            # Add item location filter to only show items from US-based sellers
            params['filter'] += ',itemLocationCountry:US'
            
            logger.info(f"Searching eBay for: {keywords}")
            response = requests.get(search_url, headers=self.headers, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.search_listings(keywords, category_id, max_results)
            
            response.raise_for_status()
            data = response.json()
            
            items = []
            if 'itemSummaries' in data:
                items = data['itemSummaries']
                logger.info(f"Found {len(items)} listings for '{keywords}'")
            
            # Respect rate limiting
            time.sleep(Config.API_CALL_DELAY_SECONDS)
            
            return items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"eBay search failed: {e}")
            return []
    
    def get_all_silver_listings(self) -> List[Dict]:
        """
        Search for silver listings across all configured keywords and categories
        """
        all_items = []
        seen_item_ids = set()
        
        # Search in coins category
        for keyword in Config.SEARCH_KEYWORDS:
            items = self.search_listings(keyword, Config.EBAY_CATEGORY_COINS)
            for item in items:
                item_id = item.get('itemId')
                if item_id and item_id not in seen_item_ids:
                    all_items.append(item)
                    seen_item_ids.add(item_id)
        
        # Search in bullion category
        for keyword in ['silver bullion', 'silver bars', 'silver rounds']:
            items = self.search_listings(keyword, Config.EBAY_CATEGORY_BULLION)
            for item in items:
                item_id = item.get('itemId')
                if item_id and item_id not in seen_item_ids:
                    all_items.append(item)
                    seen_item_ids.add(item_id)
        
        logger.info(f"Total unique listings found: {len(all_items)}")
        return all_items
    
    def get_all_gold_listings(self) -> List[Dict]:
        """
        Search for gold listings across all configured keywords and categories
        Excludes items with 'bezel' in the title (jewelry settings)
        """
        all_items = []
        seen_item_ids = set()
        
        # Keywords to exclude from gold search (jewelry-related)
        exclude_keywords = ['bezel', 'setting', 'mount', 'ring', 'pendant', 'chain']
        
        # Search in coins category
        for keyword in Config.GOLD_SEARCH_KEYWORDS:
            items = self.search_listings(keyword, Config.EBAY_CATEGORY_COINS)
            for item in items:
                item_id = item.get('itemId')
                title = item.get('title', '').lower()
                
                # Skip items with exclude keywords
                if any(exclude_kw in title for exclude_kw in exclude_keywords):
                    logger.debug(f"Skipping gold item with exclude keyword: {item.get('title', '')[:50]}...")
                    continue
                    
                if item_id and item_id not in seen_item_ids:
                    all_items.append(item)
                    seen_item_ids.add(item_id)
        
        # Search in bullion category for gold
        for keyword in ['gold bullion', 'gold bars', 'gold rounds']:
            items = self.search_listings(keyword, Config.EBAY_CATEGORY_BULLION)
            for item in items:
                item_id = item.get('itemId')
                title = item.get('title', '').lower()
                
                # Skip items with exclude keywords
                if any(exclude_kw in title for exclude_kw in exclude_keywords):
                    logger.debug(f"Skipping gold item with exclude keyword: {item.get('title', '')[:50]}...")
                    continue
                    
                if item_id and item_id not in seen_item_ids:
                    all_items.append(item)
                    seen_item_ids.add(item_id)
        
        logger.info(f"Total unique gold listings found: {len(all_items)}")
        return all_items
    
    def extract_item_details(self, item: Dict) -> Dict:
        """
        Extract relevant details from eBay item response
        """
        try:
            # Basic item info
            item_id = item.get('itemId', '')
            title = item.get('title', '')
            
            # Anti-scam filter - skip items with scam keywords
            scam_keywords = ['replica', 'plated', 'clad', 'copy', 'tribute', 'repair', 'parts']
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in scam_keywords):
                logger.debug(f"Skipping scam item: {title[:50]}...")
                return None
            
            # Gold jewelry filter - skip items with jewelry-related keywords
            # This excludes bezels, settings, rings, pendants, and chains
            jewelry_keywords = ['bezel', 'setting', 'mount', 'ring', 'pendant', 'chain', 'necklace', 'bracelet']
            if any(keyword in title_lower for keyword in jewelry_keywords):
                logger.debug(f"Skipping gold jewelry item: {title[:50]}...")
                return None
            
            price = float(item.get('price', {}).get('value', 0))
            currency = item.get('price', {}).get('currency', 'USD')
            item_url = item.get('itemWebUrl', '')
            
            # Check if listing has ended (itemEndDate is available in search results)
            # Note: quantityAvailable is NOT available in search results, only in getItem API
            item_end_date = item.get('itemEndDate')
            if item_end_date:
                try:
                    from datetime import timezone
                    end_date = datetime.fromisoformat(item_end_date.replace('Z', '+00:00'))
                    if end_date < datetime.now(timezone.utc):
                        logger.debug(f"Skipping ended listing: {title[:50]}...")
                        return None
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse itemEndDate: {e}")
            
            # Shipping cost
            shipping_cost = 0.0
            shipping_options = item.get('shippingOptions', [])
            if shipping_options and len(shipping_options) > 0:
                shipping_cost = float(shipping_options[0].get('shippingCost', {}).get('value', 0))
            
            # Seller info
            seller = item.get('seller', {})
            seller_username = seller.get('username', '')
            seller_feedback = float(seller.get('feedbackPercentage', 0))
            
            # Condition
            condition = item.get('condition', 'Unknown')
            if isinstance(condition, dict):
                condition = condition.get('conditionName', 'Unknown')
            
            return {
                'item_id': item_id,
                'title': title,
                'price': price,
                'currency': currency,
                'shipping_cost': shipping_cost,
                'total_cost': price + shipping_cost,
                'item_url': item_url,
                'seller_username': seller_username,
                'seller_feedback': seller_feedback,
                'condition': condition,
                'image_url': item.get('image', {}).get('imageUrl', ''),
                'listing_type': item.get('buyingOptions', []),
                'category_id': item.get('categoryId', ''),
                'time_listed': item.get('itemCreationDate'),  # eBay listing start time
                'item_end_date': item_end_date,  # When listing ends (for expiration tracking)
                'scan_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting item details: {e}")
            return {}
    
    def get_seller_listings(self, seller_username: str, max_results: int = 200) -> List[Dict]:
        """
        Fetch active fixed-price silver/gold listings for a specific eBay seller.

        Strategy: Use Browse API keyword searches for common silver/gold terms,
        then filter results client-side to only keep items from this specific seller.
        Uses CONCURRENT requests to avoid 502 timeout issues.

        The Finding API was decommissioned Feb 2025. The Browse API sellers:{} filter
        is not a valid/documented filter. This keyword+filter approach is the only
        reliable method using Client Credentials auth.

        Args:
            seller_username: The eBay seller's username
            max_results: Maximum number of listings to retrieve

        Returns:
            List of raw item dictionaries from eBay API
        """
        if not self.authenticate():
            logger.error("Cannot fetch seller listings: authentication failed")
            return []

        if Config.EBAY_USE_SANDBOX:
            logger.warning("Using eBay SANDBOX environment - real seller listings will NOT be found!")

        # Broader keyword set to match more listing titles
        # Include both generic and specific terms that appear in actual listings
        SELLER_SEARCH_KEYWORDS = [
            # Generic terms
            'gold',
            'silver',
            # Specific coin types
            'gold eagle',
            'silver eagle',
            'gold buffalo',
            'gold maple',
            'silver maple',
            'krugerrand',
            # US coins
            'morgan dollar',
            'peace dollar',
            'silver dollar',
            'liberty head',
            'indian head',
            'walking liberty',
            'franklin half',
            'kennedy half',
            'mercury dime',
            'junk silver',
            '90% silver',
            # Bullion
            'silver bar',
            'gold bar',
            'silver round',
            'gold round',
            'bullion',
        ]

        search_url = f"{Config.EBAY_API_BASE_URL}/item_summary/search"
        all_items = {}  # use dict keyed by itemId to deduplicate
        
        import concurrent.futures
        
        def search_keyword(keyword: str) -> List[tuple]:
            """Search for a single keyword and return items from target seller."""
            try:
                params = {
                    'q': keyword,
                    'limit': 100,
                    'filter': f'buyingOptions:{{FIXED_PRICE}},deliveryCountry:US',
                    'fieldgroups': 'EXTENDED',
                    'sort': 'newlyListed',
                }
                
                logger.info(f"Searching '{keyword}' for seller {seller_username}")
                response = requests.get(search_url, headers=self.headers, params=params, timeout=15)
                
                if response.status_code == 429:
                    logger.warning(f"Rate limited on '{keyword}'")
                    return []
                    
                if response.status_code != 200:
                    logger.warning(f"Search '{keyword}' returned {response.status_code}")
                    return []
                    
                data = response.json()
                items = data.get('itemSummaries', [])
                
                # Filter to only items from target seller
                seller_items = [
                    (item.get('itemId'), item)
                    for item in items
                    if item.get('seller', {}).get('username', '').lower() == seller_username.lower()
                ]
                logger.info(f"Keyword '{keyword}': found {len(seller_items)} items from seller")
                return seller_items
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Search failed for keyword '{keyword}': {e}")
                return []
        
        # Use ThreadPoolExecutor for concurrent API calls (8 workers for faster completion)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(search_keyword, kw): kw for kw in SELLER_SEARCH_KEYWORDS}
                
                for future in concurrent.futures.as_completed(futures, timeout=45):
                    keyword = futures[future]
                    try:
                        items = future.result()
                        for item_id, item in items:
                            if item_id and item_id not in all_items:
                                all_items[item_id] = item
                                
                        # Early termination if we have enough results
                        if len(all_items) >= max_results:
                            logger.info(f"Reached max_results ({max_results}), stopping early")
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing results for '{keyword}': {e}")
                        
        except concurrent.futures.TimeoutError:
            logger.warning("Timeout while searching keywords, returning partial results")
        except Exception as e:
            logger.error(f"Error in concurrent search: {e}")
        
        # Sort by price (highest first) for consistent ordering
        result = list(all_items.values())
        result.sort(key=lambda x: float(x.get('price', {}).get('value', 0)), reverse=True)
        
        # Limit to max_results
        result = result[:max_results]
        
        logger.info(f"Total seller listings fetched: {len(result)}")
        return result

    def test_connection(self) -> bool:
        """
        Test eBay API connection
        """
        if not self.authenticate():
            return False
        
        try:
            # Simple search to test connection
            items = self.search_listings("test", max_results=1)
            return True
        except Exception as e:
            logger.error(f"eBay API connection test failed: {e}")
            return False