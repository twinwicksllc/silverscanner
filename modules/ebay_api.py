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
        Fetch all active fixed-price listings for a specific eBay seller.
        Uses the Finding API findItemsBySeller call - the correct way to get all listings from a seller.

        Args:
            seller_username: The eBay seller's username
            max_results: Maximum number of listings to retrieve

        Returns:
            List of raw item dictionaries from eBay API (converted to Browse API format for compatibility)
        """
        if not self.authenticate():
            logger.error("Cannot fetch seller listings: authentication failed")
            return []

        # Warn if using sandbox - sandbox has very limited test data
        if Config.EBAY_USE_SANDBOX:
            logger.warning(f"Using eBay SANDBOX environment - real seller listings will NOT be found!")
            logger.warning(f"Set EBAY_USE_SANDBOX=False in environment to use production API")

        try:
            # Use Finding API findItemsBySeller - the correct API for fetching seller's listings
            # Note: Browse API sellers:{username} filter is NOT a valid/supported filter!
            if Config.EBAY_USE_SANDBOX:
                finding_url = "https://svcs.sandbox.ebay.com/services/search/FindingService/v1"
            else:
                finding_url = "https://svcs.ebay.com/services/search/FindingService/v1"

            all_items = []
            page_number = 1
            entries_per_page = 100  # Finding API max per page

            while len(all_items) < max_results:
                # Finding API uses different headers and parameters
                params = {
                    'OPERATION-NAME': 'findItemsBySeller',
                    'SECURITY-APPNAME': Config.EBAY_CLIENT_ID,
                    'RESPONSE-DATA-FORMAT': 'JSON',
                    'REST-PAYLOAD': '',
                    'sellerName': seller_username,
                    'paginationInput.entriesPerPage': min(entries_per_page, max_results - len(all_items)),
                    'paginationInput.pageNumber': page_number,
                    'itemFilter(0).name': 'ListingType',
                    'itemFilter(0).value': 'FixedPrice',
                }

                logger.info(f"Fetching seller listings page {page_number} for: {seller_username}")
                
                # Finding API uses different headers - no Authorization header needed for this call
                finding_headers = {
                    'X-EBAY-SOA-SECURITY-APPNAME': Config.EBAY_CLIENT_ID,
                    'X-EBAY-SOA-OPERATION-NAME': 'findItemsBySeller',
                    'Accept': 'application/json',
                }
                
                response = requests.get(finding_url, headers=finding_headers, params=params)

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                logger.info(f"Finding API response status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Finding API error response: {response.text}")
                    response.raise_for_status()

                data = response.json()
                
                # Parse Finding API response format
                find_response = data.get('findItemsBySellerResponse', [{}])[0]
                search_result = find_response.get('searchResult', [{}])[0]
                pagination = find_response.get('paginationOutput', [{}])[0]
                
                total_entries = int(pagination.get('totalEntries', [0])[0])
                items = search_result.get('item', [])
                
                logger.info(f"Finding API reports total entries: {total_entries}, page items: {len(items)}")

                if not items:
                    logger.info("No items returned in this page, stopping pagination")
                    break

                # Convert Finding API format to Browse API format for compatibility with seller_checker.py
                converted_items = []
                for item in items:
                    converted = self._convert_finding_to_browse_format(item)
                    if converted:
                        converted_items.append(converted)

                all_items.extend(converted_items)
                page_number += 1

                logger.info(f"Fetched {len(all_items)}/{total_entries} listings for seller '{seller_username}'")

                # Stop if we've fetched all available items
                if len(all_items) >= total_entries or len(all_items) >= max_results:
                    break

                time.sleep(Config.API_CALL_DELAY_SECONDS)

            logger.info(f"Total seller listings fetched: {len(all_items)}")
            return all_items

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch seller listings: {e}")
            return []

    def _convert_finding_to_browse_format(self, finding_item: Dict) -> Optional[Dict]:
        """
        Convert Finding API item format to Browse API item format.
        This ensures compatibility with seller_checker.py which expects Browse API format.
        """
        try:
            # Extract basic info from Finding API format
            item_id = finding_item.get('itemId', [''])[0]
            title = finding_item.get('title', [''])[0]
            
            # Price
            selling_status = finding_item.get('sellingStatus', [{}])[0]
            current_price = selling_status.get('currentPrice', [{}])[0]
            price = float(current_price.get('__value__', 0))
            currency = current_price.get('@currencyId', 'USD')
            
            # URL
            view_item_url = finding_item.get('viewItemURL', [''])[0]
            
            # Image
            gallery_url = finding_item.get('galleryURL', [''])[0]
            
            # Seller info
            seller_info = finding_item.get('sellerInfo', [{}])[0]
            seller_username = seller_info.get('sellerUserName', [''])[0]
            feedback_percent = seller_info.get('positiveFeedbackPercent', ['0'])[0]
            
            # Shipping
            shipping_info = finding_item.get('shippingInfo', [{}])[0]
            shipping_cost_val = shipping_info.get('shippingServiceCost', [{}])[0]
            shipping_cost = float(shipping_cost_val.get('__value__', 0)) if shipping_cost_val else 0.0
            
            # Listing type
            listing_info = finding_item.get('listingInfo', [{}])[0]
            listing_type = listing_info.get('listingType', ['FixedPrice'])[0]
            
            # Category
            primary_category = finding_item.get('primaryCategory', [{}])[0]
            category_id = primary_category.get('categoryId', [''])[0]
            
            # Condition
            condition = finding_item.get('condition', [{}])[0]
            condition_name = condition.get('conditionDisplayName', ['Unknown'])[0]

            # Return in Browse API format
            return {
                'itemId': item_id,
                'title': title,
                'price': {
                    'value': str(price),
                    'currency': currency
                },
                'itemWebUrl': view_item_url,
                'image': {
                    'imageUrl': gallery_url
                },
                'seller': {
                    'username': seller_username,
                    'feedbackPercentage': feedback_percent
                },
                'shippingOptions': [{
                    'shippingCost': {
                        'value': str(shipping_cost),
                        'currency': currency
                    }
                }],
                'buyingOptions': [listing_type],
                'categoryId': category_id,
                'condition': condition_name,
            }

        except Exception as e:
            logger.error(f"Error converting Finding API item: {e}")
            return None

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