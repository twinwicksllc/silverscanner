# CRITICAL FIX: eBay API quantityAvailable Field Does Not Exist

## Root Cause Confirmed

After reviewing the official eBay Browse API documentation, I've confirmed that the `ItemSummary` type returned by the `/item_summary/search` endpoint does **NOT** include a `quantityAvailable` field.

### Fields Available in ItemSummary (Search Results):
- itemId, title, price, condition, seller, shippingOptions
- itemWebUrl, image, itemCreationDate, itemEndDate
- bidCount, currentBidPrice (for auctions)
- categories, leafCategoryIds
- **NO quantityAvailable**

### The Problem Code (ebay_api.py, lines 165-168):
```python
quantity_available = item.get('quantityAvailable', 0)  # Always returns 0!
if quantity_available == 0:
    logger.debug(f"Skipping sold-out item: {title[:50]}...")
    return None  # ALL items are filtered out!
```

### Impact:
- `item.get('quantityAvailable', 0)` always returns `0` (the default)
- Every single listing is filtered out
- Scanner returns zero results

## The Fix

Remove the incorrect quantity filter from search results. The `quantityAvailable` field is only available when calling the `getItem` endpoint for individual items, not in search results.

### Alternative Approach:
Use `itemEndDate` to check if a listing has ended (expired), which IS available in search results.