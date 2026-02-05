# Gold Support Implementation Plan

## Philosophy: Pattern-Based Recognition vs. Hardcoded Lists

Instead of hardcoding specific coin names, we'll use intelligent pattern matching to identify:
- Gold content indicators (14k, 18k, 22k, 24k, .999, .9999)
- Weight indicators (1 oz, 1/10 oz, gram, dwt)
- Gold-related keywords in context
- Purity markers and hallmarks
- Common gold item categories

## Gold Item Categories to Support

### 1. Modern Bullion Coins
**Pattern Recognition:**
- "gold eagle" + weight (1 oz, 1/2 oz, 1/4 oz, 1/10 oz)
- "gold buffalo" + weight
- "gold maple" / "maple leaf" + weight
- "krugerrand" + weight
- "philharmonic" + weight
- "britannia" + weight
- "kangaroo" / "nugget" + weight
- "panda" + weight

**AGW (Actual Gold Weight):**
- 1 oz = 1.0000 oz
- 1/2 oz = 0.5000 oz
- 1/4 oz = 0.2500 oz
- 1/10 oz = 0.1000 oz

### 2. Pre-1933 US Gold Coins
**Pattern Recognition:**
- "$20" + "double eagle" / "liberty" / "saint gaudens"
- "$10" + "eagle" / "liberty" / "indian"
- "$5" + "half eagle" / "liberty" / "indian"
- "$2.50" / "$2.5" + "quarter eagle" / "liberty" / "indian"
- "$3" + "princess" / "indian"
- "$1" + "gold dollar" / "liberty"

**AGW by Denomination:**
- $20 Double Eagle: 0.9675 oz
- $10 Eagle: 0.48375 oz
- $5 Half Eagle: 0.24187 oz
- $2.50 Quarter Eagle: 0.12094 oz
- $3 Indian Princess: 0.14512 oz
- $1 Gold Dollar: 0.04837 oz

### 3. Foreign Gold Coins
**Pattern Recognition:**
- "sovereign" (British): 0.2354 oz
- "franc" + "gold" (French/Swiss): varies
- "ducat" (Austrian/Dutch): 0.1107 oz
- "peso" + "gold" (Mexican): varies
- "mark" + "gold" (German): varies
- "guilder" + "gold" (Dutch): varies

### 4. Gold Bars & Rounds
**Pattern Recognition:**
- Weight + "gold bar" / "gold round"
- "1 oz gold", "10 oz gold", "1 kilo gold"
- "gram gold bar" (1g, 5g, 10g, 20g, 50g, 100g)
- Brand names: "PAMP", "Credit Suisse", "Perth Mint", "Valcambi"

**Common Weights:**
- 1 gram = 0.03215 oz
- 5 grams = 0.16075 oz
- 10 grams = 0.3215 oz
- 20 grams = 0.643 oz
- 1 oz = 1.0000 oz
- 10 oz = 10.0000 oz
- 1 kilo = 32.15 oz

### 5. Gold Jewelry (Scrap Gold)
**Pattern Recognition:**
- Karat + "gold" (10k, 14k, 18k, 22k, 24k)
- Weight + karat (e.g., "5 grams 14k")
- "scrap gold", "gold jewelry lot"
- "gold chain", "gold bracelet", "gold ring"

**Gold Content by Karat:**
- 10k = 41.7% pure (0.417)
- 14k = 58.3% pure (0.583)
- 18k = 75.0% pure (0.750)
- 22k = 91.7% pure (0.917)
- 24k = 99.9% pure (0.999)

**Calculation:**
```python
agw = weight_in_oz * (karat / 24.0)
```

### 6. Gold Commemoratives & Proofs
**Pattern Recognition:**
- "proof" + "gold"
- "commemorative" + "gold"
- "mint set" + "gold"
- Year + "gold" + coin type

### 7. Gold Nuggets & Raw Gold
**Pattern Recognition:**
- "gold nugget" + weight
- "natural gold" + weight
- "placer gold" + weight
- "gold specimen" + weight

## Intelligent Pattern Matching System

### Multi-Stage Recognition

```python
class GoldRecognizer:
    def __init__(self):
        self.patterns = {
            'bullion_coins': [
                r'(?:american\s+)?gold\s+eagle\s+(\d+(?:/\d+)?)\s*oz',
                r'gold\s+buffalo\s+(\d+(?:/\d+)?)\s*oz',
                r'(?:canadian\s+)?(?:gold\s+)?maple\s+leaf\s+(\d+(?:/\d+)?)\s*oz',
                r'krugerrand\s+(\d+(?:/\d+)?)\s*oz',
                # ... more patterns
            ],
            'pre_1933': [
                r'\$?20\s+(?:dollar\s+)?(?:double\s+)?eagle',
                r'\$?10\s+(?:dollar\s+)?eagle',
                r'\$?5\s+(?:dollar\s+)?(?:half\s+)?eagle',
                # ... more patterns
            ],
            'bars_rounds': [
                r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)s?\s+gold\s+(?:bar|round)',
                r'(\d+)\s*(?:gram|g)\s+gold\s+bar',
                r'(\d+)\s*(?:kilo|kg)\s+gold',
                # ... more patterns
            ],
            'jewelry': [
                r'(\d+)k\s+gold',
                r'(\d+)\s*(?:gram|g|dwt)\s+(\d+)k',
                r'scrap\s+gold.*?(\d+)k',
                # ... more patterns
            ]
        }
    
    def identify_gold_item(self, title: str, description: str = "") -> Dict:
        """
        Intelligently identify gold content from title and description
        Returns: {
            'identified': bool,
            'category': str,
            'agw': float,
            'purity': float,
            'confidence': float
        }
        """
        text = f"{title} {description}".lower()
        
        # Try each category
        for category, patterns in self.patterns.items():
            result = self._match_category(text, category, patterns)
            if result['identified']:
                return result
        
        return {'identified': False}
    
    def _match_category(self, text, category, patterns):
        # Implementation for each category
        pass
```

### Context-Aware Weight Extraction

```python
class WeightExtractor:
    def extract_weight(self, text: str) -> Dict:
        """
        Extract weight from text with context awareness
        Handles: oz, grams, dwt, pennyweight, troy oz
        """
        patterns = [
            # Ounces
            (r'(\d+(?:\.\d+)?)\s*(?:troy\s+)?(?:oz|ounce)s?', 'oz'),
            # Fractions
            (r'(\d+)/(\d+)\s*oz', 'fraction'),
            # Grams
            (r'(\d+(?:\.\d+)?)\s*(?:gram|g)s?', 'grams'),
            # Pennyweight
            (r'(\d+(?:\.\d+)?)\s*(?:dwt|pennyweight)s?', 'dwt'),
            # Kilos
            (r'(\d+(?:\.\d+)?)\s*(?:kilo|kg)s?', 'kilo'),
        ]
        
        for pattern, unit in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._convert_to_oz(match, unit)
        
        return None
```

### Purity Detection

```python
class PurityDetector:
    def detect_purity(self, text: str) -> float:
        """
        Detect gold purity from various indicators
        Returns: purity as decimal (0.0 to 1.0)
        """
        # Karat system
        karat_match = re.search(r'(\d+)k(?:arat)?', text, re.IGNORECASE)
        if karat_match:
            karat = int(karat_match.group(1))
            return karat / 24.0
        
        # Fineness (999, 9999, etc.)
        fineness_match = re.search(r'\.?(999+)', text)
        if fineness_match:
            fineness = fineness_match.group(1)
            return float(f"0.{fineness}")
        
        # Percentage
        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:pure\s+)?gold', text, re.IGNORECASE)
        if percent_match:
            return float(percent_match.group(1)) / 100.0
        
        # Default assumptions by category
        if 'eagle' in text or 'buffalo' in text or 'maple' in text:
            return 0.9999  # Modern bullion is typically .9999
        
        if 'krugerrand' in text:
            return 0.9167  # 22k
        
        return 1.0  # Assume pure if no indicator
```

## Smart Filtering & Exclusions

### Anti-Scam Filters
```python
GOLD_EXCLUSION_KEYWORDS = [
    'plated',
    'filled',
    'overlay',
    'tone',
    'color',
    'replica',
    'copy',
    'fake',
    'costume',
    'fashion',
    'imitation',
    'gold-colored',
    'gold colored',
    'gold tone',
    'gold-tone',
    'not real gold',
    'not actual gold',
    'gold appearance',
    'looks like gold',
]
```

### Minimum Value Filters
```python
# Only consider items with significant gold content
MIN_GOLD_VALUE = 50.0  # Minimum $50 in gold content
MIN_AGW = 0.01  # Minimum 0.01 oz AGW (about $20-30)
```

## Database Schema Updates

```sql
-- Add metal type support
ALTER TABLE deals ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver';
ALTER TABLE deals ADD COLUMN metal_purity FLOAT DEFAULT 1.0;
ALTER TABLE deals RENAME COLUMN silver_weight_oz TO metal_weight_oz;

-- Add indexes for performance
CREATE INDEX idx_deals_metal_type ON deals(metal_type);
CREATE INDEX idx_deals_metal_weight ON deals(metal_weight_oz);

-- Add spot price tracking for multiple metals
CREATE TABLE spot_prices (
    id SERIAL PRIMARY KEY,
    metal_type VARCHAR(20) NOT NULL,
    price FLOAT NOT NULL,
    source VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_spot_prices_metal_timestamp ON spot_prices(metal_type, timestamp DESC);
```

## Configuration Updates

```python
# config.py additions

# Metal types enabled
METALS_ENABLED = ['silver', 'gold']  # Can add 'platinum', 'palladium' later

# Metal-specific thresholds
METAL_THRESHOLDS = {
    'silver': 89.0,  # 89% of spot
    'gold': 92.0,    # 92% of spot (gold has tighter spreads)
    'platinum': 90.0,
    'palladium': 90.0
}

# Metal-specific search keywords
GOLD_SEARCH_KEYWORDS = [
    'gold eagle',
    'gold buffalo',
    'gold maple',
    'krugerrand',
    'gold sovereign',
    'double eagle',
    '$20 gold',
    '$10 gold',
    'gold bar',
    'gold round',
    '14k gold',
    '18k gold',
    'scrap gold',
]

# eBay category IDs
EBAY_CATEGORIES = {
    'silver': '39487',  # Silver Bullion
    'gold': '39482',    # Gold Bullion
}
```

## Spot Price Fetching for Gold

```python
class MultiMetalSpotPrice:
    def __init__(self):
        self.sources = {
            'silver': ['jm_bullion', 'kitco', 'google_finance'],
            'gold': ['kitco', 'gold_api', 'google_finance'],
        }
    
    def get_spot_price(self, metal_type: str) -> Dict:
        """
        Get spot price for any supported metal
        """
        if metal_type == 'gold':
            return self._get_gold_spot()
        elif metal_type == 'silver':
            return self._get_silver_spot()
        # ... etc
    
    def _get_gold_spot(self) -> Dict:
        """
        Fetch gold spot price from multiple sources
        """
        # Try Kitco first
        try:
            price = self._fetch_kitco_gold()
            if price:
                return {'spot_price': price, 'source': 'Kitco', 'verified': True}
        except:
            pass
        
        # Try Gold API (if available)
        try:
            price = self._fetch_gold_api()
            if price:
                return {'spot_price': price, 'source': 'Gold API', 'verified': True}
        except:
            pass
        
        # Fallback to Google Finance
        return self._fetch_google_finance_gold()
```

## Deal Calculation for Gold

```python
def calculate_gold_deal_metrics(item_details: Dict, agw: float, spot_price: float) -> Dict:
    """
    Calculate deal metrics for gold items
    """
    total_cost = item_details['price'] + item_details['shipping_cost']
    cost_per_oz = total_cost / agw if agw > 0 else 0
    
    # Calculate threshold (e.g., 92% of spot for gold)
    threshold = spot_price * (METAL_THRESHOLDS['gold'] / 100.0)
    
    # Calculate discount
    discount_percent = ((spot_price - cost_per_oz) / spot_price) * 100
    savings_per_oz = spot_price - cost_per_oz
    
    return {
        'spot_price': spot_price,
        'cost_per_oz': cost_per_oz,
        'discount_percent': discount_percent,
        'savings_per_oz': savings_per_oz,
        'threshold': threshold,
        'is_deal': cost_per_oz <= threshold
    }
```

## Testing Strategy

### Test Cases
1. **Modern Bullion**: "2024 1 oz American Gold Eagle BU"
2. **Fractional**: "1/10 oz Gold Maple Leaf"
3. **Pre-1933**: "$20 Saint Gaudens Double Eagle MS63"
4. **Foreign**: "British Gold Sovereign"
5. **Bars**: "10 gram PAMP Suisse Gold Bar"
6. **Jewelry**: "14k Gold Chain 15 grams"
7. **Mixed Lot**: "Lot of 5 Gold Coins Mixed"
8. **Edge Cases**: "Gold-plated coin" (should reject)

## Implementation Steps

1. **Day 1: Core Infrastructure**
   - Create `GoldCalculator` class
   - Implement pattern recognition system
   - Add gold spot price fetching
   - Database schema updates

2. **Day 2: Integration**
   - Integrate with existing scanner
   - Update eBay search to include gold
   - Modify deal detection logic
   - Add gold-specific filters

3. **Day 3: Testing & UI**
   - Comprehensive testing
   - Update dashboard to show metal type
   - Add metal filter dropdown
   - Documentation

## Success Metrics

- Successfully identify 90%+ of gold items
- Accurate AGW calculations within 1%
- No false positives (gold-plated items)
- Deal detection working correctly
- Performance: scan completes in <60 seconds

Would you like me to start implementing this?
