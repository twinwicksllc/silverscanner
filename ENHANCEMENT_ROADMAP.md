# Silver Scanner Enhancement Roadmap

## Current State
The scanner currently focuses exclusively on silver coins and bullion with:
- ASW (Actual Silver Weight) calculations
- Deal detection based on silver spot price
- Support for common US silver coins (Morgan, Peace, Walking Liberty, etc.)
- eBay API integration for listings

## Proposed Enhancements

### 1. Multi-Metal Support (Gold, Platinum, Palladium)

#### Phase 1: Gold Support
**Priority: HIGH**

**Implementation:**
- Add gold spot price fetching (similar to silver)
- Create `AGW` (Actual Gold Weight) calculator
- Add gold coin types:
  - American Gold Eagle (1 oz, 1/2 oz, 1/4 oz, 1/10 oz)
  - American Gold Buffalo (1 oz)
  - Canadian Gold Maple Leaf
  - South African Krugerrand
  - Austrian Philharmonic
  - Pre-1933 US Gold Coins ($20 Double Eagle, $10 Eagle, $5 Half Eagle, $2.50 Quarter Eagle)
  - Gold bars (1 oz, 10 oz, 1 kg)

**Database Changes:**
```sql
ALTER TABLE deals ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver';
ALTER TABLE deals ADD COLUMN metal_weight_oz FLOAT;
ALTER TABLE deals RENAME COLUMN silver_weight_oz TO metal_weight_oz;
```

**Configuration:**
```python
METALS_ENABLED = ['silver', 'gold', 'platinum', 'palladium']
GOLD_THRESHOLD_PERCENTAGE = 85.0  # Different threshold for gold
PLATINUM_THRESHOLD_PERCENTAGE = 87.0
```

**Estimated Effort:** 2-3 days

#### Phase 2: Platinum & Palladium Support
**Priority: MEDIUM**

**Platinum Coins:**
- American Platinum Eagle
- Canadian Platinum Maple Leaf
- Platinum bars

**Palladium Coins:**
- Canadian Palladium Maple Leaf
- Palladium bars

**Estimated Effort:** 1-2 days

---

### 2. Advanced Filtering & Search

#### Multi-Criteria Filtering
**Priority: HIGH**

**Features:**
- Filter by metal type (silver, gold, platinum)
- Filter by coin type (Morgan, Peace, Eagle, etc.)
- Filter by discount percentage range (e.g., 10-20% off)
- Filter by price range
- Filter by seller rating
- Filter by condition (BU, MS65+, circulated, etc.)
- Filter by listing age (new today, last 24h, last week)

**UI Enhancement:**
```html
<div class="filters">
  <select id="metal-filter">
    <option value="all">All Metals</option>
    <option value="silver">Silver</option>
    <option value="gold">Gold</option>
    <option value="platinum">Platinum</option>
  </select>
  
  <select id="discount-filter">
    <option value="all">All Discounts</option>
    <option value="10-15">10-15% off</option>
    <option value="15-20">15-20% off</option>
    <option value="20+">20%+ off</option>
  </select>
  
  <input type="text" id="search-filter" placeholder="Search titles...">
</div>
```

**Estimated Effort:** 1 day

---

### 3. Watchlist & Alerts

#### Personal Watchlist
**Priority: HIGH**

**Features:**
- Save specific searches (e.g., "Morgan Dollars under $70")
- Track specific coin types
- Get notified when deals match watchlist criteria
- Email/SMS alerts for watchlist matches

**Database Schema:**
```sql
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    name VARCHAR(100),
    metal_type VARCHAR(20),
    coin_type VARCHAR(100),
    max_price FLOAT,
    min_discount FLOAT,
    alert_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Estimated Effort:** 2 days

---

### 4. Historical Price Tracking & Analytics

#### Price History Charts
**Priority: MEDIUM**

**Features:**
- Track spot price history for all metals
- Track average deal prices over time
- Show price trends (7-day, 30-day, 90-day)
- Compare current deals to historical averages
- Identify "best time to buy" patterns

**Visualization:**
- Line charts for spot price trends
- Bar charts for deal frequency
- Heatmaps for best deal times (day of week, time of day)

**Estimated Effort:** 2-3 days

---

### 5. Enhanced Deal Scoring

#### Intelligent Deal Ranking
**Priority: MEDIUM**

**Current:** Simple discount percentage
**Proposed:** Multi-factor scoring system

**Scoring Factors:**
1. Discount percentage (40% weight)
2. Seller reputation (20% weight)
3. Listing freshness (15% weight)
4. Condition/grade (15% weight)
5. Shipping cost (10% weight)

**Formula:**
```python
score = (
    (discount_percent / 100) * 0.40 +
    (seller_feedback / 100) * 0.20 +
    (1 - listing_age_hours / 168) * 0.15 +  # 168 hours = 1 week
    (condition_score / 100) * 0.15 +
    (1 - shipping_cost / max_shipping) * 0.10
) * 100
```

**Estimated Effort:** 1 day

---

### 6. Marketplace Expansion

#### Beyond eBay
**Priority: LOW-MEDIUM**

**Additional Marketplaces:**
- **APMEX** - Direct scraping of deals section
- **JM Bullion** - Sale items
- **SD Bullion** - Clearance section
- **Reddit r/Pmsforsale** - Private sales (with caution)
- **Facebook Marketplace** - Local deals
- **Craigslist** - Local deals

**Challenges:**
- Different APIs/scraping methods for each
- Varying data quality
- Anti-scraping measures
- Authentication requirements

**Estimated Effort:** 3-5 days per marketplace

---

### 7. User Accounts & Personalization

#### Multi-User Support
**Priority: LOW**

**Features:**
- User registration/login
- Personal settings (thresholds, preferences)
- Saved searches
- Deal history (what you've viewed/purchased)
- Portfolio tracking (what you own)

**Database Schema:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_settings (
    user_id INTEGER REFERENCES users(id),
    setting_key VARCHAR(50),
    setting_value TEXT,
    PRIMARY KEY (user_id, setting_key)
);

CREATE TABLE user_portfolio (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    metal_type VARCHAR(20),
    coin_type VARCHAR(100),
    quantity INTEGER,
    purchase_price FLOAT,
    purchase_date DATE
);
```

**Estimated Effort:** 5-7 days

---

### 8. Mobile App

#### Native Mobile Experience
**Priority: LOW**

**Platforms:**
- iOS (Swift/SwiftUI)
- Android (Kotlin/Jetpack Compose)
- Or: React Native for both

**Features:**
- Push notifications for deals
- Quick deal browsing
- Saved searches
- Portfolio tracking
- Price alerts

**Estimated Effort:** 4-6 weeks

---

### 9. API for Third-Party Integration

#### Public API
**Priority: LOW**

**Endpoints:**
```
GET /api/v1/deals - Get current deals
GET /api/v1/spot-prices - Get current spot prices
GET /api/v1/metals/{metal}/history - Get price history
POST /api/v1/watchlist - Create watchlist item
```

**Authentication:**
- API keys
- Rate limiting
- Usage tiers (free, premium)

**Estimated Effort:** 2-3 days

---

### 10. Advanced Features

#### Machine Learning Enhancements
**Priority: LOW**

**Features:**
- Predict future spot prices
- Identify fake/scam listings automatically
- Recommend deals based on user behavior
- Detect price manipulation patterns

**Estimated Effort:** 2-4 weeks

---

## Implementation Priority

### Phase 1 (Next 1-2 weeks)
1. ✅ Fix scan_id issue (COMPLETED)
2. 🔄 Multi-metal support (Gold)
3. 🔄 Advanced filtering
4. 🔄 Watchlist & alerts

### Phase 2 (Next 1-2 months)
5. Historical price tracking
6. Enhanced deal scoring
7. Platinum/Palladium support

### Phase 3 (Next 3-6 months)
8. Marketplace expansion (APMEX, JM Bullion)
9. User accounts
10. Mobile app (if demand exists)

### Phase 4 (Future)
11. Public API
12. Machine learning features

---

## Technical Considerations

### Architecture Changes Needed

**For Multi-Metal Support:**
```python
# Current structure
class ASWCalculator:
    def calculate_asw(self, item_details) -> Dict:
        # Silver-specific logic
        pass

# Proposed structure
class MetalCalculator:
    def __init__(self, metal_type: str):
        self.metal_type = metal_type
        self.calculator = self._get_calculator()
    
    def _get_calculator(self):
        calculators = {
            'silver': SilverCalculator(),
            'gold': GoldCalculator(),
            'platinum': PlatinumCalculator(),
            'palladium': PalladiumCalculator()
        }
        return calculators.get(self.metal_type)
    
    def calculate_weight(self, item_details) -> Dict:
        return self.calculator.calculate(item_details)
```

**For Multiple Marketplaces:**
```python
class MarketplaceAdapter:
    def get_listings(self) -> List[Dict]:
        raise NotImplementedError

class EbayAdapter(MarketplaceAdapter):
    def get_listings(self) -> List[Dict]:
        # eBay-specific logic
        pass

class ApmexAdapter(MarketplaceAdapter):
    def get_listings(self) -> List[Dict]:
        # APMEX-specific logic
        pass

class MarketplaceAggregator:
    def __init__(self):
        self.adapters = [
            EbayAdapter(),
            ApmexAdapter(),
            JMBullionAdapter()
        ]
    
    def get_all_listings(self) -> List[Dict]:
        all_listings = []
        for adapter in self.adapters:
            all_listings.extend(adapter.get_listings())
        return all_listings
```

---

## Cost Considerations

### Additional API Costs
- **Gold/Platinum/Palladium spot prices:** Free (same sources as silver)
- **Additional marketplaces:** Varies (some free, some paid)
- **SMS alerts:** ~$0.01 per message (Twilio)
- **Push notifications:** Free (Firebase)
- **Hosting:** May need to upgrade Render plan for increased traffic

### Development Time
- **Solo developer:** 3-6 months for Phase 1-2
- **Small team (2-3):** 1-2 months for Phase 1-2

---

## Revenue Opportunities (Optional)

If you want to monetize:

1. **Premium Tier ($9.99/month)**
   - Unlimited watchlists
   - SMS/push alerts
   - Advanced filtering
   - Historical data access
   - Priority support

2. **Affiliate Links**
   - Earn commission on purchases through your links
   - Partner with APMEX, JM Bullion, etc.

3. **API Access**
   - Free tier: 100 requests/day
   - Paid tier: $29/month for 10,000 requests/day

---

## Next Steps

1. **Decide on priorities** - Which features are most important to you?
2. **Start with gold support** - Easiest high-impact enhancement
3. **Gather user feedback** - What do users want most?
4. **Iterate quickly** - Release features incrementally

Would you like me to start implementing any of these enhancements?
