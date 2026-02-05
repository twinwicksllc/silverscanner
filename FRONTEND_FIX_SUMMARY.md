# Frontend Metal Filter Switching Fix

## Problem
When switching to gold on the dashboard and running a scan:
- ✅ Gold spot price displays correctly
- ❌ Silver chart still shows (not gold chart)
- ❌ Silver "found deals" still show (not gold deals)

## Root Cause
The frontend was not refreshing the deals table and price history chart when the metal filter was changed. Only the current price was being updated.

## Fixes Applied

### 1. Frontend JavaScript (`static/js/app.js`)

#### Added `fetchPriceHistory()` function
```javascript
async function fetchPriceHistory(metalType = null) {
    const metal = metalType || AppState.currentMetal || 'silver';
    
    try {
        const response = await fetch(`/api/price/history?metal_type=${metal}&days=30`);
        const data = await response.json();
        
        if (data.success) {
            updatePriceChart(data.data);
        }
    } catch (error) {
        console.error('Error fetching price history:', error);
    }
}
```

#### Updated `filterByMetal()` function
Now fetches all three data types when switching metals:
```javascript
function filterByMetal() {
    const selectedMetal = metalFilter.value;
    AppState.currentMetal = selectedMetal;
    
    // Update UI labels
    updateMetalLabels(selectedMetal);
    
    // Fetch deals for selected metal
    fetchDeals(selectedMetal);
    
    // Update price info for selected metal
    fetchPriceInfo(selectedMetal);
    
    // Update price history chart for selected metal (NEW!)
    fetchPriceHistory(selectedMetal);
}
```

### 2. Backend API (`app.py`)

#### Updated `/api/price/history` endpoint
Now supports `metal_type` parameter:
```python
@app.route('/api/price/history')
def api_price_history():
    days = request.args.get('days', 30, type=int)
    metal_type = request.args.get('metal_type', 'silver').lower()
    
    if metal_type not in ['silver', 'gold']:
        return jsonify({'success': False, 'error': 'Invalid metal_type'}), 400
    
    price_history = db_manager.get_price_history(days=days, metal_type=metal_type)
    
    return jsonify({
        'success': True,
        'data': price_history,
        'count': len(price_history)
    })
```

### 3. Database Model (`database/models.py`)

#### Updated `PriceHistory` model
Added `metal_type` column to support multiple metals:
```python
class PriceHistory(Base):
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    metal_type = Column(String(20), default='silver', index=True)  # NEW!
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    price = Column(Float, nullable=False)
    source = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Updated `save_price_history()` method
Now accepts `metal_type` parameter:
```python
def save_price_history(self, price: float, source: str = None, metal_type: str = 'silver') -> bool:
    price_history = PriceHistory(
        metal_type=metal_type,
        price=price,
        source=source
    )
```

#### Updated `get_price_history()` method
Now filters by `metal_type`:
```python
def get_price_history(self, days: int = 30, metal_type: str = 'silver') -> list:
    query = session.query(PriceHistory).filter(
        PriceHistory.timestamp >= cutoff_date,
        PriceHistory.metal_type == metal_type
    ).order_by(PriceHistory.timestamp.asc()).all()
```

### 4. Migration Endpoint (`app.py`)

Added new migration endpoint to update `price_history` table:
```
POST /admin/migrate/price_history_metal_type
```

## Deployment Steps

### Step 1: Wait for Render Deployment
The code has been pushed to GitHub (commit 6c48e09). Wait 2-3 minutes for Render to deploy.

### Step 2: Run the Migration
After deployment completes, run this command to add the `metal_type` column:

```bash
curl -X POST https://scanner.teckstart.com/admin/migrate/price_history_metal_type \
  -H "X-Migration-Key: teckstart_migrate_2025"
```

Expected response:
```json
{
  "success": true,
  "message": "Price history metal_type migration completed",
  "columns_added": ["metal_type"],
  "indexes_created": ["idx_price_history_metal_type", "idx_price_history_metal_timestamp"]
}
```

### Step 3: Test the Dashboard
1. Visit https://scanner.teckstart.com/
2. Switch metal filter from Silver to Gold
3. Verify:
   - ✅ Gold spot price displays
   - ✅ Gold deals table shows (or "No deals found")
   - ✅ Gold price history chart shows (will be empty initially)
4. Switch back to Silver
5. Verify:
   - ✅ Silver spot price displays
   - ✅ Silver deals table shows
   - ✅ Silver price history chart shows

## Important Notes

### Price History Chart
The gold price history chart will be empty initially because:
1. No gold price history has been saved yet
2. The scanner needs to run at least once with gold selected
3. After running a gold scan, price history will start accumulating

### Data Migration
Existing `price_history` records will be updated with `metal_type = 'silver'` automatically during the migration.

### Backward Compatibility
- All changes are backward compatible
- Silver functionality remains unchanged
- New gold features don't affect existing silver data

## Files Modified
1. `static/js/app.js` - Added fetchPriceHistory() and updated filterByMetal()
2. `app.py` - Updated /api/price/history endpoint, added migration endpoint
3. `database/models.py` - Updated PriceHistory model and related methods
4. `migrations/add_metal_type_to_price_history.sql` - New migration script

## Next Steps After Deployment
1. Run the migration command above
2. Test metal filter switching
3. Run a gold scan to start collecting gold price history
4. Verify all UI elements update correctly when switching metals