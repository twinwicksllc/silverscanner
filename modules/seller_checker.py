"""
Seller Listing Price Checker Module
Analyzes a seller's own eBay listings against current live spot prices
to identify listings that may be priced too low given rising metal prices.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from modules.ebay_api import eBayAPI
from modules.asw_calculator import ASWCalculator
from modules.gold_calculator import GoldCalculator
from modules.multi_metal_spot_price import MultiMetalSpotPrice

logger = logging.getLogger(__name__)

# ─── Alert thresholds ────────────────────────────────────────────────────────
# How far below fair-value your listing price is before we flag it.
ALERT_CRITICAL_PCT  = 15.0   # >15% below fair value → RED  (raise ASAP)
ALERT_WARNING_PCT   =  5.0   # 5-15% below fair value → YELLOW (watch closely)
# ≥ -5% (at or above 95% of fair value)  → GREEN (ok)

# Typical buyer-premium bands used to estimate "fair retail value"
# i.e. what a competitive seller charges above raw melt value
PREMIUM_ESTIMATES = {
    'silver': 0.08,   # ~8% over melt for common silver
    'gold':   0.04,   # ~4% over melt for common gold
}


class SellerChecker:
    """
    Checks a seller's own active eBay listings against current spot prices
    and reports which ones are priced too low.
    """

    def __init__(self):
        self.ebay_api       = eBayAPI()
        self.asw_calculator = ASWCalculator()
        self.gold_calculator = GoldCalculator()
        self.spot_price     = MultiMetalSpotPrice()

    # ─── Public entry point ──────────────────────────────────────────────────

    def check_seller_listings(
        self,
        seller_username: str,
        metal_filter: str = 'all',          # 'silver', 'gold', or 'all'
        max_listings: int = 400,
    ) -> Dict:
        """
        Fetch all active listings for *seller_username* and analyse pricing.

        Returns a dict::
            {
              'seller':        str,
              'checked_at':    ISO-timestamp,
              'spot_prices':   {'silver': float, 'gold': float},
              'total_fetched': int,
              'total_analyzed': int,
              'listings':      [ <listing_result>, … ]   # sorted: worst first
            }

        Each listing_result::
            {
              'item_id', 'title', 'item_url', 'image_url',
              'your_price', 'shipping_cost', 'total_cost',
              'metal_type',          # 'silver' | 'gold' | 'unknown'
              'detected_oz',         # troy oz of pure metal (None if unknown)
              'melt_value',          # spot × oz  (None if unknown)
              'fair_value',          # melt_value × (1 + premium) (None if unknown)
              'gap_pct',             # (your_price - fair_value) / fair_value × 100
                                     # negative = underpriced, positive = overpriced
              'alert',               # 'critical' | 'warning' | 'ok' | 'unknown'
              'suggested_price',     # fair_value rounded to nearest $0.50
              'gain_if_repriced',    # suggested_price - your_price
            }
        """
        logger.info(f"=== Seller Listing Check: @{seller_username} | filter={metal_filter} ===")

        # 1. Get live spot prices for both metals up-front
        spot_prices = self._fetch_spot_prices()
        logger.info(f"Live spot prices → Silver: ${spot_prices.get('silver', 0):.2f}/oz  "
                    f"Gold: ${spot_prices.get('gold', 0):.2f}/oz")

        # 2. Fetch all active seller listings from eBay
        raw_items = self.ebay_api.get_seller_listings(
            seller_username, max_results=max_listings, metal_filter=metal_filter
        )
        
        # Check if we're using sandbox (which won't have real data)
        from config import Config
        sandbox_warning = None
        if Config.EBAY_USE_SANDBOX:
            sandbox_warning = "WARNING: Using eBay SANDBOX environment. Real seller listings cannot be retrieved. Set EBAY_USE_SANDBOX=False in production."
        
        if not raw_items:
            logger.warning(f"No listings found for seller '{seller_username}'")
            result = self._empty_result(seller_username, spot_prices)
            if sandbox_warning:
                result['warning'] = sandbox_warning
            return result

        logger.info(f"Fetched {len(raw_items)} listings for @{seller_username}")

        # 3. Analyse each listing
        results = []
        for item in raw_items:
            result = self._analyse_listing(item, spot_prices)
            if result is None:
                continue  # skip items that couldn't be parsed at all

            # Apply metal_filter
            if metal_filter != 'all' and result['metal_type'] != metal_filter:
                continue

            results.append(result)

        # 4. Sort: critical first, then warning, then ok, then unknown
        priority = {'critical': 0, 'warning': 1, 'ok': 2, 'unknown': 3}
        results.sort(key=lambda r: (priority.get(r['alert'], 4), r.get('gap_pct', 0)))

        summary_counts = {
            'critical': sum(1 for r in results if r['alert'] == 'critical'),
            'warning':  sum(1 for r in results if r['alert'] == 'warning'),
            'ok':       sum(1 for r in results if r['alert'] == 'ok'),
            'unknown':  sum(1 for r in results if r['alert'] == 'unknown'),
        }

        logger.info(f"Analysis complete → {summary_counts}")

        return {
            'seller':          seller_username,
            'checked_at':      datetime.now().isoformat(),
            'spot_prices':     spot_prices,
            'total_fetched':   len(raw_items),
            'total_analyzed':  len(results),
            'summary':         summary_counts,
            'listings':        results,
        }

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _fetch_spot_prices(self) -> Dict[str, Optional[float]]:
        """Fetch live spot prices for silver and gold."""
        prices = {}
        try:
            silver_info = self.spot_price.get_silver_price_info()
            prices['silver'] = silver_info.get('spot_price')
        except Exception as e:
            logger.error(f"Failed to get silver spot price: {e}")
            prices['silver'] = None

        try:
            gold_info = self.spot_price.get_gold_price_info()
            prices['gold'] = gold_info.get('spot_price')
        except Exception as e:
            logger.error(f"Failed to get gold spot price: {e}")
            prices['gold'] = None

        return prices

    def _analyse_listing(self, item: Dict, spot_prices: Dict) -> Optional[Dict]:
        """
        Analyse a single raw eBay item dict and return a pricing result dict.
        Returns None if the item cannot be meaningfully parsed.
        """
        try:
            item_id  = item.get('itemId', '')
            title    = item.get('title', '')
            item_url = item.get('itemWebUrl', '')
            image_url = item.get('image', {}).get('imageUrl', '')

            # Skip scam/replica items (using global config)
            scam_kw = Config.SEARCH_EXCLUDE_KEYWORDS
            title_lower = title.lower()
            if any(kw in title_lower for kw in scam_kw):
                logger.debug(f"Skipping item (scam/excluded keyword): {title[:60]}")
                return None

            # Price
            price_obj    = item.get('price', {})
            your_price   = float(price_obj.get('value', 0))
            if your_price <= 0:
                return None

            # Shipping cost
            shipping_cost = 0.0
            for opt in item.get('shippingOptions', []):
                sc = opt.get('shippingCost', {}).get('value')
                if sc is not None:
                    shipping_cost = float(sc)
                    break
            total_cost = your_price + shipping_cost

            # ── Detect metal type and oz content ──────────────────────────
            metal_type  = 'unknown'
            detected_oz = None

            # Try silver first
            # Note: asw_calculator returns key 'asw', gold_calculator returns key 'agw'
            silver_result = self.asw_calculator.calculate_asw(item)
            if silver_result and silver_result.get('asw') and silver_result['asw'] > 0:
                metal_type  = 'silver'
                detected_oz = silver_result['asw']
            else:
                # Try gold
                gold_result = self.gold_calculator.calculate_agw(item)
                if gold_result and gold_result.get('agw') and gold_result['agw'] > 0:
                    metal_type  = 'gold'
                    detected_oz = gold_result['agw']
                else:
                    # Keyword-based fallback for metal type (no oz estimate)
                    if any(kw in title_lower for kw in ['silver', 'ag ', 'troy oz silver']):
                        metal_type = 'silver'
                    elif any(kw in title_lower for kw in ['gold', 'au ', 'troy oz gold', 'karat', 'kt gold']):
                        metal_type = 'gold'

            # ── Compute melt/fair value if we have oz + spot price ─────────
            spot = spot_prices.get(metal_type) if metal_type != 'unknown' else None

            melt_value    = None
            fair_value    = None
            gap_pct       = None
            alert         = 'unknown'
            suggested_price = None
            gain_if_repriced = None

            if detected_oz and spot:
                premium    = PREMIUM_ESTIMATES.get(metal_type, 0.06)
                melt_value = round(detected_oz * spot, 2)
                fair_value = round(melt_value * (1 + premium), 2)

                # gap relative to fair value (negative = underpriced)
                gap_pct = round(((your_price - fair_value) / fair_value) * 100, 1)

                if gap_pct < -ALERT_CRITICAL_PCT:
                    alert = 'critical'
                elif gap_pct < -ALERT_WARNING_PCT:
                    alert = 'warning'
                else:
                    alert = 'ok'

                # Suggested price: round up to nearest $0.50
                suggested_price = round(fair_value * 2) / 2
                gain_if_repriced = round(suggested_price - your_price, 2)

            return {
                'item_id':          item_id,
                'title':            title,
                'item_url':         item_url,
                'image_url':        image_url,
                'your_price':       your_price,
                'shipping_cost':    shipping_cost,
                'total_cost':       total_cost,
                'metal_type':       metal_type,
                'detected_oz':      detected_oz,
                'metal_purity':    silver_result.get('purity') if metal_type == 'silver' else (gold_result.get('purity') if metal_type == 'gold' else 1.0),
                'coin_type':       silver_result.get('type') if metal_type == 'silver' else (gold_result.get('type') if metal_type == 'gold' else 'Other'),
                'melt_value':       melt_value,
                'fair_value':       fair_value,
                'spot_price_used':  spot,
                'gap_pct':          gap_pct,
                'alert':            alert,
                'suggested_price':  suggested_price,
                'gain_if_repriced': gain_if_repriced,
            }

        except Exception as e:
            logger.error(f"Error analysing listing '{item.get('title', '')}': {e}")
            return None

    @staticmethod
    def _empty_result(seller: str, spot_prices: Dict) -> Dict:
        return {
            'seller':         seller,
            'checked_at':     datetime.now().isoformat(),
            'spot_prices':    spot_prices,
            'total_fetched':  0,
            'total_analyzed': 0,
            'summary':        {'critical': 0, 'warning': 0, 'ok': 0, 'unknown': 0},
            'listings':       [],
        }