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
        for keyword in Config.SILVER_SEARCH_KEYWORDS:
            items = self.search_listings(keyword, Config.EBAY_CATEGORY_COINS)
            for item in items:
                item_id = item.get('itemId')
                if item_id and item_id not in seen_item_ids:
                    all_items.append(item)
                    seen_item_ids.add(item_id)
        
        # Search in bullion category
        for keyword in Config.SILVER_BULLION_KEYWORDS:
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
        Excludes items with forbidden keywords in the title (jewelry settings, replicas, etc.)
        """
        all_items = []
        seen_item_ids = set()
        
        # Keywords to exclude from gold search (jewelry-related)
        exclude_keywords = Config.SEARCH_EXCLUDE_KEYWORDS
        
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
        for keyword in Config.GOLD_BULLION_KEYWORDS:
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
    
    def get_seller_listings(self, seller_username: str, max_results: int = 400,
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

        # eBay Browse API requires a real keyword in 'q'.
        # Scope the query to the requested metal so results are more relevant.
        # NOTE: For 'all', use a broad query to catch more items
        _METAL_QUERIES = {
            'silver': 'silver',
            'gold':   'gold',
            'all':    'silver|gold|coin|bullion|bar|round',   
        }
        q_term = _METAL_QUERIES.get(metal_filter, 'coin')

        from urllib.parse import urlencode

        try:
            while len(all_items) < max_results:
                # Build standard params (q, limit, offset, fieldgroups) via urlencode so they
                # are properly encoded, then append the filter string RAW so that the curly
                # braces and pipe characters are NOT percent-encoded.  eBay's API rejects the
                # encoded form (%7B…%7D) and returns 0 results silently.
                base_params = {
                    'q':          q_term,
                    'limit':      page_size,
                    'offset':     offset,
                    'fieldgroups': 'EXTENDED',
                }
                filter_str = (
                    f'sellers:{{{seller_username}}},'
                    f'buyingOptions:{{FIXED_PRICE|AUCTION}}'
                )
                full_url = f"{search_url}?{urlencode(base_params)}&filter={filter_str}"

                logger.info(f"Fetching page offset={offset} for seller '{seller_username}'")
                logger.debug(f"Request URL: {full_url}")
                response = requests.get(full_url, headers=self.headers, timeout=20)

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 10))
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                if response.status_code != 200:
                    logger.warning(
                        f"sellers filter returned HTTP {response.status_code}: {response.text[:400]}"
                    )
                    logger.info("Falling back to keyword-based search...")
                    return self._get_seller_listings_by_keywords(seller_username, max_results, metal_filter)

                data = response.json()
                items = data.get('itemSummaries', [])
                total = data.get('total', 0)
                warnings = data.get('warnings', [])

                if warnings:
                    logger.warning(f"eBay API warnings on sellers filter: {warnings}")

                logger.info(f"Page offset={offset}: got {len(items)} items (total available: {total})")

                # If the first page comes back empty the sellers filter returned nothing —
                # log the full response body and fall back to keyword-based search.
                if not items and offset == 0:
                    logger.warning(
                        f"sellers filter returned 0 results (total=0). "
                        f"Raw response: {response.text[:600]}"
                    )
                    logger.info("Falling back to keyword-based search...")
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
        Fallback: run multiple sellers-filtered searches, each with a single keyword,
        to work around the fact that eBay's sellers filter requires a non-empty `q`.
        This is more reliable than a global keyword search because we're always filtering
        to this specific seller — we just vary the keyword to catch all listing types.
        """
        from urllib.parse import urlencode
        import concurrent.futures

        search_url = f"{Config.EBAY_API_BASE_URL}/item_summary/search"
        all_items = {}

        _SILVER_KEYWORDS = [
            'silver', 'gold', 'coin', 'bullion', 'morgan', 'peace', 'eagle',
            'liberty', 'dollar', 'half', 'dime', 'quarter', 'bar', 'round',
        ]
        _GOLD_KEYWORDS = [
            'gold', 'silver', 'coin', 'bullion', 'eagle', 'buffalo',
            'maple', 'sovereign', 'bar', 'round',
        ]

        if metal_filter == 'silver':
            keywords = _SILVER_KEYWORDS
        elif metal_filter == 'gold':
            keywords = _GOLD_KEYWORDS
        else:
            # For 'all', use a combined deduplicated list
            combined = _SILVER_KEYWORDS + [k for k in _GOLD_KEYWORDS if k not in _SILVER_KEYWORDS]
            keywords = combined

        logger.info(
            f"Keyword fallback: trying {len(keywords)} sellers-filter queries "
            f"for '{seller_username}' (filter={metal_filter})..."
        )

        def search_with_seller_filter(keyword: str) -> List[tuple]:
            """Search using sellers filter + one keyword. Returns list of (item_id, item)."""
            try:
                base_params = {
                    'q':           keyword,
                    'limit':       100,
                    'offset':      0,
                    'fieldgroups': 'EXTENDED',
                }
                filter_str = (
                    f'sellers:{{{seller_username}}},'
                    f'buyingOptions:{{FIXED_PRICE|AUCTION}}'
                )
                full_url = f"{search_url}?{urlencode(base_params)}&filter={filter_str}"
                response = requests.get(full_url, headers=self.headers, timeout=15)

                if response.status_code != 200:
                    logger.debug(f"Keyword '{keyword}' sellers-filter: HTTP {response.status_code}")
                    return []

                data = response.json()
                items = data.get('itemSummaries', [])
                total = data.get('total', 0)

                if items:
                    logger.info(
                        f"Keyword '{keyword}' sellers-filter: {len(items)}/{total} items "
                        f"(total available for this seller+keyword)"
                    )
                return [(item.get('itemId'), item) for item in items if item.get('itemId')]

            except Exception as e:
                logger.error(f"sellers-filter keyword '{keyword}' failed: {e}")
                return []

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = {executor.submit(search_with_seller_filter, kw): kw for kw in keywords}
                for future in concurrent.futures.as_completed(futures, timeout=60):
                    try:
                        for item_id, item in future.result():
                            if item_id not in all_items:
                                all_items[item_id] = item
                        if len(all_items) >= max_results:
                            break
                    except Exception as e:
                        logger.error(f"Error processing sellers-filter keyword result: {e}")
        except concurrent.futures.TimeoutError:
            logger.warning("Keyword fallback timeout — returning partial results")

        result = list(all_items.values())[:max_results]

        if result:
            logger.info(
                f"Keyword fallback found {len(result)} items for seller '{seller_username}'"
            )
        else:
            logger.warning(
                f"Keyword fallback found 0 items for seller '{seller_username}' "
                f"after trying {len(keywords)} keyword+sellers-filter combinations. "
                f"Check that the username is correct and the seller has active listings."
            )

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