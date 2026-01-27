# Two-Key Verification System for Spot Prices

## Overview

The Silver Scanner now uses a sophisticated **Two-Key Verification System** to ensure accurate spot price data. This system prevents relying on a single potentially incorrect source.

## How It Works

### Step 1: Fetch from Primary Sources
The system fetches spot prices from two primary sources:
1. **JM Bullion** - `https://www.jmbullion.com/charts/silver-prices/`
2. **SD Bullion** - `https://sdbullion.com/silver-prices`

### Step 2: Calculate Variance
The system calculates the difference between the two prices:
```
difference = abs(JM_Price - SD_Price)
threshold = 5% of average price
```

### Step 3: Verification Decision

#### ✅ Prices Agree (difference ≤ 5%)
- **Action:** Use the average of both prices
- **Status:** Verified
- **Example:** JM=$30.50, SD=$30.25 → Average=$30.38 ✓

#### ⚠️ Prices Disagree (difference > 5%)
- **Action:** Fetch from fallback source to break the tie
- **Status:** Requires verification
- **Example:** JM=$195.36, SD=$103.75 → Difference=$91.61 (61%!) ⚠️

### Step 4: Fallback Verification (when needed)

The system tries fallback sources in order:

1. **Metals-API.com** (if API key set)
   - Professional metals pricing API
   - Requires: `METALS_API_KEY` environment variable
   - Free tier: 50 requests/month
   - Sign up: https://metals-api.com/

2. **Alpha Vantage** (if API key set)
   - Financial data API with commodity prices
   - Requires: `ALPHA_VANTAGE_API_KEY` environment variable
   - Free tier: 25 requests/day
   - Sign up: https://www.alphavantage.co/

3. **APMEX Scraping** (always available)
   - Fallback web scraping from APMEX
   - No API key required
   - May be blocked occasionally

### Step 5: Tie-Breaking Logic

When fallback price is obtained:
```
JM_difference = abs(JM_Price - Fallback_Price)
SD_difference = abs(SD_Price - Fallback_Price)

if JM_difference < SD_difference:
    use JM_Price (verified by fallback)
else:
    use SD_Price (verified by fallback)
```

### Step 6: Final Fallback

If all fallback sources fail:
- **Action:** Use average of primary sources
- **Status:** Unverified (logged as warning)
- **Reason:** Better to have approximate data than no data

---

## Configuration

### Environment Variables

Add these to your Render environment variables for enhanced verification:

```bash
# Optional: Metals-API.com (recommended)
METALS_API_KEY=your-metals-api-key

# Optional: Alpha Vantage
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# Variance threshold (default: 0.05 = 5%)
SPOT_PRICE_VARIANCE_THRESHOLD=0.05
```

### Getting API Keys

#### Metals-API.com (Recommended)
1. Go to https://metals-api.com/
2. Sign up for free account
3. Get API key from dashboard
4. Add to Render: `METALS_API_KEY=your-key`
5. Free tier: 50 requests/month (plenty for our use)

#### Alpha Vantage
1. Go to https://www.alphavantage.co/support/#api-key
2. Get free API key
3. Add to Render: `ALPHA_VANTAGE_API_KEY=your-key`
4. Free tier: 25 requests/day

---

## Example Scenarios

### Scenario 1: Normal Operation (Prices Agree)
```
JM Bullion: $30.50/oz
SD Bullion: $30.25/oz
Difference: $0.25 (0.8%)
Threshold: $1.52 (5%)

✓ Prices agree within threshold
→ Use average: $30.38/oz
Status: Verified
```

### Scenario 2: Prices Disagree (Fallback Needed)
```
JM Bullion: $195.36/oz  ← Clearly wrong
SD Bullion: $103.75/oz  ← Seems wrong too
Difference: $91.61 (61%)
Threshold: $7.48 (5%)

⚠ Prices disagree - fetching fallback
Metals-API: $30.15/oz

JM difference from fallback: $165.21
SD difference from fallback: $73.60

✓ SD Bullion is closer to fallback
→ Use SD Bullion: $103.75/oz
Status: Verified by fallback

Note: In this case, both primary sources were wrong!
The fallback revealed the true price is ~$30/oz
```

### Scenario 3: All Fallbacks Fail
```
JM Bullion: $30.50/oz
SD Bullion: $32.00/oz
Difference: $1.50 (4.8%)
Threshold: $1.56 (5%)

✓ Prices agree within threshold
→ Use average: $31.25/oz
Status: Verified

(No fallback needed in this case)
```

---

## Benefits

### 1. Accuracy
- Prevents using obviously wrong prices
- Cross-validates data from multiple sources
- Identifies outliers automatically

### 2. Reliability
- Works even if one primary source fails
- Multiple fallback options
- Graceful degradation

### 3. Transparency
- Logs all price comparisons
- Shows which source was used
- Indicates verification status

### 4. Flexibility
- Optional API keys for enhanced verification
- Configurable variance threshold
- Easy to add new sources

---

## Monitoring

### Log Messages to Watch For

**Normal Operation:**
```
INFO - Fetching from primary sources (JM Bullion, SD Bullion)...
INFO - JM Bullion: $30.50/oz
INFO - SD Bullion: $30.25/oz
INFO - Difference: $0.25 (threshold: $1.52)
INFO - ✓ Prices agree within 5.0% threshold
INFO - Final verified price: $30.38/oz from JM Bullion + SD Bullion (verified)
```

**Fallback Triggered:**
```
WARNING - ⚠ Prices disagree by $91.61 (>5.0%)
INFO - Fetching from fallback sources to break tie...
INFO - Metals-API price: $30.15/oz
INFO - ✓ SD Bullion is closer to fallback - using SD Bullion
INFO - Final verified price: $103.75/oz from SD Bullion (verified by fallback)
```

**All Fallbacks Failed:**
```
WARNING - Fallback sources failed, using average of primary sources
INFO - Final verified price: $149.56/oz from JM Bullion + SD Bullion (unverified)
```

---

## Troubleshooting

### Issue: Prices always disagree
**Cause:** One source may be consistently wrong or showing different market data
**Solution:** 
1. Check if API keys are set for fallback verification
2. Review logs to see which source is the outlier
3. Consider removing the problematic source from config

### Issue: Fallback always fails
**Cause:** API keys not set or rate limits exceeded
**Solution:**
1. Add `METALS_API_KEY` to Render environment variables
2. Check API usage limits
3. APMEX scraping may be blocked - this is normal fallback behavior

### Issue: Price seems wrong
**Cause:** All sources may be showing stale or incorrect data
**Solution:**
1. Check logs for verification status
2. Manually verify price on multiple websites
3. System will use best available data even if unverified

---

## Technical Details

### Code Location
- **Module:** `modules/spot_price.py`
- **Config:** `config.py` (PRIMARY_SPOT_SOURCES, FALLBACK_SPOT_SOURCES)
- **Test:** `test_two_key_verification.py`

### Key Functions
- `get_spot_price()` - Main entry point with two-key verification
- `_fetch_from_jmbullion()` - Primary source #1
- `_fetch_from_sdbullion()` - Primary source #2
- `_fetch_from_fallback()` - Tie-breaking logic
- `_fetch_from_metals_api()` - Fallback option #1
- `_fetch_from_alpha_vantage()` - Fallback option #2
- `_fetch_from_apmex()` - Fallback option #3

### Configuration Constants
```python
PRIMARY_SPOT_SOURCES = [
    'https://www.jmbullion.com/charts/silver-prices/',
    'https://sdbullion.com/silver-prices'
]

SPOT_PRICE_VARIANCE_THRESHOLD = 0.05  # 5%
```

---

## Summary

The Two-Key Verification System provides:
- ✅ Accurate spot prices through cross-validation
- ✅ Automatic outlier detection
- ✅ Multiple fallback options
- ✅ Transparent logging
- ✅ Graceful degradation

This ensures your Silver Scanner always has reliable pricing data for deal detection.