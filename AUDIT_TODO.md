# Silver Scanner - Comprehensive Code Audit

## Audit Objectives
1. **Verify Deal Math** - Ensure only precious metal content is being priced correctly
2. **Check Quantity Filtering** - Verify zero-quantity items are properly filtered
3. **Validate Expiration Logic** - Ensure expired listings are removed
4. **Review Search Quality** - Confirm we're finding real deals, not junk
5. **Assess Seller Filtering** - Verify unreliable sellers are excluded
6. **Evaluate Deal Scoring** - Check "how good" calculation accuracy
7. **Test Removal Logic** - Confirm unavailable listings are removed
8. **Verify Scheduling** - Ensure regular checks are working

## Audit Sections

### Section 1: ASW (Actual Silver Weight) Calculation
- [ ] Review ASW values for each coin type
- [ ] Verify quantity multipliers are applied correctly
- [ ] Check face value calculations for junk silver
- [ ] Ensure total silver weight is accurate

### Section 2: Deal Math & Pricing
- [ ] Verify cost_per_oz calculation: total_cost / silver_weight_oz
- [ ] Check discount_percent calculation
- [ ] Validate threshold comparison logic
- [ ] Ensure shipping is included in total cost

### Section 3: eBay API & Filtering
- [ ] Review quantity_available capture
- [ ] Check zero-quantity filtering
- [ ] Verify scam keyword filtering
- [ ] Review seller feedback filtering

### Section 4: Database & Cleanup
- [ ] Check expunge routine logic
- [ ] Verify zero-quantity removal
- [ ] Review deal persistence (UPSERT)
- [ ] Check cleanup timing

### Section 5: Spot Price Accuracy
- [ ] Verify two-key verification
- [ ] Check fallback chain
- [ ] Review cache behavior

### Section 6: Potential Enhancements
- [ ] Multi-metal support (gold, platinum)
- [ ] Better deal scoring algorithm
- [ ] Historical price tracking
- [ ] Alert improvements

## Files to Audit
1. modules/asw_calculator.py - Silver weight calculations
2. modules/ebay_api.py - eBay API and filtering
3. modules/deal_scanner.py - Deal detection logic
4. modules/spot_price.py - Price fetching
5. database/models.py - Data persistence
6. config.py - Configuration values
7. app.py - API endpoints and scheduling