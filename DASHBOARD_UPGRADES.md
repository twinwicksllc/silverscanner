# Dashboard Upgrades - Scan Status, Relative Timing, and Deal Lifecycle

## Overview
Three major upgrades to make the dashboard feel more alive and functional:
1. Enhanced Scan Status card with real-time statistics
2. Relative timing display (Time Ago format)
3. Complete deal lifecycle management with hide/archive functionality

## 1. Scan Status Card Upgrade

### Problem
The original Scan Status card was too basic with just a checkmark and "Ready" text. It didn't show any statistics about the actual scan.

### Solution

**Enhanced Display:**
- Shows scan duration (e.g., "2m 14s" or "45s")
- Displays total listings processed (e.g., "452 listings checked")
- More informative status messages
- Real-time updates during and after scans

**Backend Implementation:**
```python
# Track scan start/end times
scan_start_time = datetime.now()
# ... perform scan ...
scan_end_time = datetime.now()

# Save to database
db_manager.save_scan_history({
    'start_time': scan_start_time,
    'end_time': scan_end_time,
    # ... other fields ...
})
```

**Duration Calculation:**
```python
# In get_last_scan()
if last_scan.end_time:
    diff = last_scan.end_time - last_scan.start_time
    seconds = diff.total_seconds()
    if seconds < 60:
        duration = f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        duration = f"{minutes}m {seconds}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        duration = f"{hours}h {minutes}m"
```

**Frontend Display:**
```html
<div class="status-card">
    <h3>Scan Status</h3>
    <div class="value">
        {% if is_scanning %}
            <span class="loading"></span>
            Scanning
        {% elif last_scan %}
            ✓ Ready
        {% else %}
            ⏳ Ready
        {% endif %}
    </div>
    <div class="subtext">
        {% if is_scanning %}
            In progress...
        {% elif last_scan %}
            {% if last_scan.duration %}
                Last scan: {{ last_scan.duration }}
            {% endif %}
            {% if last_scan.total_listings_scanned %}
                <br>{{ last_scan.total_listings_scanned }} listings checked
            {% endif %}
        {% else %}
            Ready to scan
        {% endif %}
    </div>
</div>
```

## 2. Relative Timing (Time Ago Format)

### Problem
The Details column showed absolute timestamps (e.g., "Jan 28, 2026, 01:48 AM") which wasn't as useful for understanding deal freshness. Multiple items had the same timestamp, suggesting they might be showing scan time instead of listing time.

### Solution

**Enhanced Display:**
- Shows "Listed 14 minutes ago" instead of absolute timestamps
- Uses existing `time_since_listed` calculation
- Makes deals feel more fresh and live
- Reflects actual eBay listing time, not scan time

**Implementation:**
- Already implemented in `_deal_to_dict()` method
- Calculates time difference from `deal.time_listed` (eBay listing start time)
- Formats as "X minutes ago", "X hours ago", "X days ago"
- Uses user's configured timezone for display

**Frontend:**
```html
<td>
    {% if deal.condition_tags %}
        {{ deal.condition_tags|join(' ') }}
    {% else %}
        {{ deal.condition }}
    {% endif %}
    <br>
    <small>Listed {{ deal.time_since_listed }}</small>
</td>
```

## 3. Deal Lifecycle & Cleanup

### Problem
Deals would stay in the dashboard indefinitely even if:
- They were no longer interesting to the user
- They were sold/ended on eBay
- The user wanted to dismiss them manually

### Solution

**Auto-Removal (Cleanup):**
```python
def cleanup_expired_deals(self) -> int:
    """Remove deals that are no longer active on eBay (older than 7 days)"""
    session = self.get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        expired_deals = session.query(Deal).filter(
            Deal.qualified_at < cutoff
        ).delete()
        
        session.commit()
        logger.info(f"Cleaned up {expired_deals} expired deals")
        return expired_deals
    except Exception as e:
        session.rollback()
        logger.error(f"Error cleaning up expired deals: {e}")
        return 0
    finally:
        session.close()
```

**Manual Hide/Archive:**
- Added `is_hidden` and `hidden_at` columns to Deal model
- Hide button (🙈) on each deal row
- Hidden deals filtered from recent deals view
- Can be restored from archive

**Database Schema Changes:**
```python
class Deal(Base):
    # ... existing fields ...
    
    # Metadata
    scan_id = Column(String(50))
    qualified_at = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float)
    is_valid = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)  # NEW: User manually hidden/archived
    hidden_at = Column(DateTime)  # NEW: When the deal was hidden
```

**Hide Functionality:**
```python
def hide_deal(self, item_id: str) -> bool:
    """Hide a deal (archive it from view)"""
    session = self.get_session()
    try:
        deal = session.query(Deal).filter_by(item_id=item_id).first()
        if deal:
            deal.is_hidden = True
            deal.hidden_at = datetime.utcnow()
            session.commit()
            logger.info(f"Deal hidden: {item_id}")
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Error hiding deal: {e}")
        return False
    finally:
        session.close()
```

**Updated get_recent_deals:**
```python
def get_recent_deals(self, limit: int = 50) -> list:
    """Get recent deals from database"""
    session = self.get_session()
    try:
        deals = session.query(Deal).filter(
            Deal.is_hidden == False  # NEW: Filter out hidden deals
        ).order_by(
            Deal.qualified_at.desc()
        ).limit(limit).all()
        
        return [self._deal_to_dict(deal) for deal in deals]
    except Exception as e:
        logger.error(f"Error getting recent deals: {e}")
        return []
    finally:
        session.close()
```

## API Endpoints

### Hide a Deal
```http
POST /api/deal/hide
Content-Type: application/json

{
  "item_id": "v1|123456789012|0"
}
```

### Restore a Hidden Deal
```http
POST /api/deal/unhide
Content-Type: application/json

{
  "item_id": "v1|123456789012|0"
}
```

### Get Hidden Deals
```http
GET /api/deals/hidden?limit=50
```

### Cleanup Expired Deals
```http
POST /api/deal/cleanup
```

## Frontend Enhancements

### Scan Status Card
- Dynamic display based on scan state
- Shows duration when scan completes
- Shows listings checked count
- Visual loading indicator during scan

### Archive Button
```html
<button class="btn btn-secondary" onclick="showHiddenDeals()">
    📁 Archived
</button>
```

### Hide Button on Each Deal
```html
<button 
    class="hide-btn" 
    onclick="hideDeal('{{ deal.item_id }}', this)"
    title="Hide this deal"
>
    🙈
</button>
```

### Archived Deals Modal
- Displays all hidden/archived deals
- Shows deal details (title, price, discount)
- Restore button for each deal
- Close button to dismiss modal

### Smooth Animations
```javascript
function hideDeal(itemId, button) {
    // ... API call ...
    if (data.success) {
        const row = button.closest('tr');
        row.style.transition = 'opacity 0.3s';
        row.style.opacity = '0';
        setTimeout(() => {
            row.remove();
        }, 300);
    }
}
```

## User Experience

### Before Upgrades:
- ✗ Basic checkmark for scan status
- ✗ No scan statistics
- ✗ Absolute timestamps (hard to read)
- ✗ No way to dismiss deals
- ✗ Deals accumulate indefinitely
- ✗ Database grows without cleanup

### After Upgrades:
- ✓ Scan duration (e.g., "2m 14s")
- ✓ Listings processed (e.g., "452 listings checked")
- ✓ Relative timing ("Listed 14 minutes ago")
- ✓ Hide button on each deal
- ✓ Archived deals modal
- ✓ Restore hidden deals
- ✓ Auto-cleanup of old deals
- ✓ Dashboard feels "live"

## Persistence

All actions persist to database:
- ✅ Hidden deals stay hidden across refreshes
- ✅ Hidden deals stay hidden across restarts
- ✅ Scan history includes duration and counts
- ✅ Settings load from database on startup
- ✅ No state lost on page refresh or server restart

## Files Modified

### Database Models (`database/models.py`)
- Added `is_hidden` and `hidden_at` to Deal model
- Updated `get_recent_deals()` to filter hidden deals
- Added `hide_deal()` method
- Added `unhide_deal()` method
- Added `get_hidden_deals()` method
- Added `cleanup_expired_deals()` method
- Updated `save_scan_history()` to accept end_time
- Updated `get_last_scan()` to calculate duration

### Application (`app.py`)
- Updated `run_background_scan()` to track start/end times
- Added `/api/deal/hide` endpoint
- Added `/api/deal/unhide` endpoint
- Added `/api/deals/hidden` endpoint
- Added `/api/deal/cleanup` endpoint

### Templates (`templates/index.html`)
- Enhanced Scan Status card display
- Added "Archived" button
- Added Actions column to deals table
- Added hide button on each deal row
- Added JavaScript functions for hide/unhide
- Added archived deals modal
- Added smooth animations

## Testing Instructions

### 1. Test Scan Status
1. Start a scan
2. Observe "Scanning..." status with loading animation
3. Wait for scan to complete
4. Verify "Last scan: Xm Ys" appears
5. Verify "X listings checked" appears

### 2. Test Hide/Archive
1. Click 🙈 on a deal row
2. Confirm hide dialog
3. Verify deal animates and disappears
4. Click "📁 Archived" button
5. Verify deal appears in modal
6. Click "🔄 Restore" on deal
7. Verify deal reappears in main table

### 3. Test Cleanup
1. Manually call cleanup API or wait for automatic cleanup
2. Verify deals older than 7 days are removed
3. Verify scan history remains intact

### 4. Test Persistence
1. Hide a deal
2. Refresh the page
3. Verify deal stays hidden
4. Check archived deals
5. Restore a deal
6. Refresh the page
7. Verify deal reappears

## Expected Behavior After Deployment

✅ Scan Status card shows duration and listing count
✅ Relative timing displays correctly
✅ Hide button works with smooth animation
✅ Archived deals modal displays correctly
✅ Restore functionality works
✅ All actions persist across refreshes
✅ Auto-cleanup removes old deals
✅ Database remains manageable
✅ Dashboard feels "live" and responsive

## Commit Info

**Commit:** `6000b59`
**Branch:** main
**Repository:** twinwicksllc/silverscanner
**Status:** Pushed successfully