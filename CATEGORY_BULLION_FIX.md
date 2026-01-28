# EBAY_CATEGORY_BULLION Fix

## Problem
Scan crashed with: `AttributeError: type object 'Config' has no attribute 'EBAY_CATEGORY_BULLION'`

## Root Cause
During the logic recovery from commit 383ef93, the `EBAY_CATEGORY_BULLION` attribute was accidentally omitted from config.py.

## Solution
**Commit:** `41febcf`

Restored the missing category ID from commit 383ef93:
```python
EBAY_CATEGORY_COINS = '112862'  # Coins & Paper Money
EBAY_CATEGORY_BULLION = '39487'  # Silver Bullion
```

## Verification
✅ Both category IDs now present in Config class
✅ Config class loads without errors
✅ Matches commit 383ef93 exactly

## Expected Result
The scan should now complete successfully without AttributeError.