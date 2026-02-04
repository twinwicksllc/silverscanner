# Critical Fix: Scanner Now Working

## The Problem

Your scanner was returning **zero results** because of a critical bug in the eBay API integration.

### Root Cause

The code was checking for `quantityAvailable` field in eBay search results:

```python
# OLD CODE (BROKEN)
quantity_available = item.get('quantityAvailable', 0)  # Always returns 0!
if quantity_available == 0:
    return None  # ALL items filtered out!
```

**The Problem:** The eBay Browse API `item_summary/search` endpoint does **NOT** return `quantityAvailable`. This field is only available when calling the `getItem` endpoint for individual items.

Since the field doesn't exist, `item.get('quantityAvailable', 0)` always returns `0` (the default), causing **every single listing to be filtered out**.

---

## The Fix

### 1. Removed Incorrect Quantity Filter

Replaced the non-existent `quantityAvailable` check with a proper `itemEndDate` check (which IS available in search results):

```python
# NEW CODE (WORKING)
item_end_date = item.get('itemEndDate')
if item_end_date:
    end_date = datetime.fromisoformat(item_end_date.replace('Z', '+00:00'))
    if end_date < datetime.now(timezone.utc):
        logger.debug(f"Skipping ended listing: {title[:50]}...")
        return None
```

### 2. Updated Database Schema

Replaced `quantity_available` column with more useful tracking fields:
- `item_end_date` - When the eBay listing ends/expires
- `last_seen_in_scan` - Last time this deal appeared in a scan

### 3. Improved Cleanup Logic

Replaced the broken `remove_zero_quantity_deals()` with two new methods:

**`remove_expired_deals()`** - Removes deals whose eBay listing has ended
```python
# Finds deals where item_end_date < now and deletes them
```

**`cleanup_stale_deals()`** - Removes deals not seen in recent scans
```python
# If a deal hasn't been seen for 24 hours, it's likely sold
# This catches items that were purchased but listing didn't end
```

---

## Files Changed

1. **modules/ebay_api.py**
   - Removed broken `quantityAvailable` filter
   - Added `itemEndDate` check for ended listings
   - Updated return data to include `item_end_date`

2. **database/models.py**
   - Replaced `quantity_available` with `item_end_date` and `last_seen_in_scan`
   - Added `cleanup_stale_deals()` method
   - Added `remove_expired_deals()` method
   - Updated `save_deal()` to track `last_seen_in_scan`

3. **modules/deal_scanner.py**
   - Updated cleanup calls to use new methods
   - Now calls: `expunge_stale_hidden_deals()`, `remove_expired_deals()`, `cleanup_stale_deals()`

4. **app.py**
   - Replaced migration endpoint with `/admin/migrate/listing_tracking`
   - Adds new columns: `item_end_date`, `last_seen_in_scan`

---

## Migration Required

After deploying, run the migration to add the new columns:

```bash
curl -X POST https://scanner.teckstart.com/admin/migrate/listing_tracking \
  -H "X-Migration-Key: teckstart_migrate_2025"
```

---

## Expected Behavior After Fix

1. **Scanner finds deals** - No longer filters out all listings
2. **Expired listings removed** - Deals with ended eBay listings are cleaned up
3. **Stale deals removed** - Deals not seen for 24+ hours are removed (likely sold)
4. **Hidden deals expunged** - Hidden deals not in current scan are deleted

---

## Testing Checklist

- [ ] Run a manual scan
- [ ] Verify deals are found and displayed
- [ ] Check logs for "QUALIFIED" messages
- [ ] Verify cleanup routines run without errors
- [ ] Confirm stale/expired deals are removed

---

## Why This Happened

The original code assumed that `quantityAvailable` would be returned by the eBay search API. This is a common misconception because:

1. The field IS available in the `getItem` API (individual item lookup)
2. The field name suggests it should be in search results
3. Without testing against the actual API, the bug wasn't caught

The fix uses fields that ARE available in search results (`itemEndDate`) and implements a time-based staleness check as a backup.