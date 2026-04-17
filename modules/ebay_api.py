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
    
    def get_seller_listings(self, seller_username: str, max_results: int = 200,
                             metal_filter: str = 'all') -> List[Dict]:
        """
        Fetch active listings for a specific eBay seller using the Browse API
        sellers:{username} filter with pagination.

        Key insight (from eBay community): The sellers:{username} filter DOES work,
        but you must explicitly include buyingOptions:{FIXED_PRICE|AUCTION} otherwise
        the API returns 0 results.

        Args:
            seller_username: The eBay seller's username
            max_results: Maximum number of listings to retrieve
            metal_filter: 'silver', 'gold', or 'all' — scopes the search query

        Returns:
            List of raw item dictionaries from eBay API
        """
        if not self.authenticate():
            logger.error("Cannot fetch seller listings: authentication failed")
            return []

        if Config.EBAY_USE_SANDBOX:
            logger.warning("Using eBay SANDBOX environment - real seller listings will NOT be found!")

        search_url = f"{Config.EBAY_API_BASE_URL}/item_summary/search"
        all_items = []
        seen_ids = set()
        offset = 0
        page_size = 100  # API max per call

        logger.info(f"Fetching listings for seller '{seller_username}' using sellers filter (filter={metal_filter})...")

        # eBay Browse API requires a real keyword in 'q' — a bare space no longer works
        # (API returns HTTP 200 with 0 results instead of an error).
        # Scope the query to the requested metal so results are more relevant.
        _METAL_QUERIES = {
            'silver': 'silver coin bullion round bar dollar half dime quarter',
            'gold':   'gold coin bullion round bar eagle buffalo maple',
            'all':    'silver gold coin bullion round bar',
        }
        BROAD_METALS_QUERY = _METAL_QUERIES.get(metal_filter, _METAL_QUERIES['all'])

        try:
            while len(all_items) < max_results:
                params = {
                    'q': BROAD_METALS_QUERY,
                    'limit': page_size,
                    'offset': offset,
                    # CRITICAL: must include both FIXED_PRICE and AUCTION or API returns 0 results
                    'filter': f'sellers:{{{seller_username}}},buyingOptions:{{FIXED_PRICE|AUCTION}}',
                    'fieldgroups': 'EXTENDED',
                }

                logger.info(f"Fetching page offset={offset} for seller '{seller_username}'")
                response = requests.get(search_url, headers=self.headers, params=params, timeout=20)

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 10))
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                if response.status_code != 200:
                    logger.warning(f"sellers filter returned {response.status_code}: {response.text[:200]}")
                    # Fall back to keyword search if sellers filter fails
                    logger.info("Falling back to keyword-based search...")
                    return self._get_seller_listings_by_keywords(seller_username, max_results, metal_filter)

                data = response.json()
                items = data.get('itemSummaries', [])
                total = data.get('total', 0)

                logger.info(f"Page offset={offset}: got {len(items)} items (total available: {total})")

                # If the first page comes back empty the sellers filter returned nothing —
                # fall back to the keyword-based approach rather than silently returning [].
                if not items and offset == 0:
                    logger.info(
                        "sellers filter returned 0 results on first page "
                        "(API may have changed or username not found); "
                        "falling back to keyword-based search..."
                    )
                    return self._get_seller_listings_by_keywords(seller_username, max_results, metal_filter)

                if not items:
                    break

                for item in items:
                    item_id = item.get('itemId')
                    if item_id and item_id not in seen_ids:
                        all_items.append(item)
                        seen_ids.add(item_id)

                offset += len(items)

                # Stop if we've got all available or reached max
                if offset >= total or len(all_items) >= max_results:
                    break

                time.sleep(0.2)  # small delay between pages

        except requests.exceptions.RequestException as e:
            logger.error(f"sellers filter request failed: {e}")
            logger.info("Falling back to keyword-based search...")
            return self._get_seller_listings_by_keywords(seller_username, max_results, metal_filter)

        logger.info(f"Total seller listings fetched: {len(all_items)}")
        return all_items[:max_results]

    def _get_seller_listings_by_keywords(self, seller_username: str, max_results: int = 200,
                                          metal_filter: str = 'all') -> List[Dict]:
        """
        Fallback: fetch seller listings by searching common silver/gold keywords
        and filtering client-side to the target seller.
        Uses concurrent requests to stay within timeout limits.
        """
        search_url = f"{Config.EBAY_API_BASE_URL}/item_summary/search"
        all_items = {}
        total_api_results = 0  # Total items found across all keywords
        seller_item_counts = []  # Track (keyword, total_found, seller_matches) for reporting

        import concurrent.futures

        _SILVER_KEYWORDS = [
            'silver', 'silver eagle', 'silver maple', 'morgan dollar',
            'peace dollar', 'silver dollar', 'liberty head', 'indian head',
            'walking liberty', 'franklin half', 'kennedy half', 'mercury dime',
            'junk silver', '90% silver', 'silver bar', 'silver round', 'silver bullion',
        ]
        _GOLD_KEYWORDS = [
            'gold', 'gold eagle', 'gold buffalo', 'gold maple', 'krugerrand',
            'gold bar', 'gold round', 'gold bullion',
        ]

        if metal_filter == 'silver':
            SELLER_SEARCH_KEYWORDS = _SILVER_KEYWORDS
            logger.info(f"Keyword fallback: searching {len(SELLER_SEARCH_KEYWORDS)} silver keywords for seller '{seller_username}'...")
        elif metal_filter == 'gold':
            SELLER_SEARCH_KEYWORDS = _GOLD_KEYWORDS
            logger.info(f"Keyword fallback: searching {len(SELLER_SEARCH_KEYWORDS)} gold keywords for seller '{seller_username}'...")
        else:
            SELLER_SEARCH_KEYWORDS = _SILVER_KEYWORDS + _GOLD_KEYWORDS
            logger.info(f"Keyword fallback: searching {len(SELLER_SEARCH_KEYWORDS)} silver+gold keywords for seller '{seller_username}'...")

        def search_keyword(keyword: str) -> tuple:
            """Search by keyword and filter results by seller. Returns (keyword, total_found, seller_items)"""
            try:
                params = {
                    'q': keyword,
                    'limit': 100,
                    'filter': 'buyingOptions:{FIXED_PRICE|AUCTION}',
                    'fieldgroups': 'EXTENDED',
                }
                response = requests.get(search_url, headers=self.headers, params=params, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Keyword '{keyword}': HTTP {response.status_code} (skipped)")
                    return (keyword, 0, [])
                
                data = response.json()
                items = data.get('itemSummaries', [])
                total_count = data.get('total', len(items))
                
                # Filter by seller username (case-insensitive)
                seller_items = [
                    (item.get('itemId'), item)
                    for item in items
                    if item.get('seller', {}).get('username', '').lower() == seller_username.lower()
                ]
                
                # Log results for this keyword (INFO level so it appears in production logs)
                if seller_items:
                    logger.info(f"Keyword '{keyword}': found {len(seller_items)}/{total_count} items from seller '{seller_username}'")
                else:
                    logger.info(f"Keyword '{keyword}': found 0/{total_count} items from seller '{seller_username}'")
                
                return (keyword, total_count, seller_items)
            except Exception as e:
                logger.error(f"Keyword search '{keyword}' failed: {e}")
                return (keyword, 0, [])

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(search_keyword, kw): kw for kw in SELLER_SEARCH_KEYWORDS}
                for future in concurrent.futures.as_completed(futures, timeout=45):
                    try:
                        keyword, total_count, seller_items = future.result()
                        total_api_results += total_count
                        seller_item_counts.append((keyword, total_count, len(seller_items)))
                        
                        for item_id, item in seller_items:
                            if item_id and item_id not in all_items:
                                all_items[item_id] = item
                        
                        if len(all_items) >= max_results:
                            break
                    except Exception as e:
                        logger.error(f"Error processing keyword result: {e}")
        except concurrent.futures.TimeoutError:
            logger.warning("Keyword search timeout, returning partial results")

        result = list(all_items.values())[:max_results]
        
        # Detailed summary logging
        seller_matches = sum(count for _, _, count in seller_item_counts)
        
        if not result:
            # Log which keywords were tried
            tried_keywords = [kw for kw, _, _ in seller_item_counts if kw]
            logger.warning(
                f"Keyword fallback found 0 items for seller '{seller_username}'. "
                f"Searched {len(SELLER_SEARCH_KEYWORDS)} keywords ({metal_filter} filter), "
                f"found {total_api_results} total eBay listings, "
                f"but 0 from this seller. "
                f"Possible causes: seller username incorrect, seller has no active listings, "
                f"or listings use keywords not in our search terms."
            )
        else:
            logger.info(f"Keyword fallback found {len(result)} items for seller '{seller_username}' "
                       f"(searched {len(SELLER_SEARCH_KEYWORDS)} keywords, checked {total_api_results} total API results)")
        
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