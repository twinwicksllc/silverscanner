# Dashboard Enhancement Plan

## Enhancement 1: Sortable Deals Table

### Features
- **Sort by Discount %**: Highest to lowest (default)
- **Sort by Price/oz**: Lowest to highest
- **Sort by Time Listed**: Newest to oldest

### Implementation
1. Add sort buttons to table headers
2. Add sorting logic to JavaScript
3. Store sort preference in AppState
4. Visual indicators for active sort column

## Enhancement 2: Zero-Quantity Deal Removal

### Features
- Track quantity available for each listing
- Filter out sold-out items (quantity = 0)
- Remove stale deals during scan
- Ensure only actionable deals are shown

### Implementation
1. Capture `quantityAvailable` from eBay API
2. Add `quantity_available` column to Deal model
3. Filter deals with quantity > 0
4. Update expunge routine to remove zero-quantity deals

## Testing Plan
1. Test sorting by each column
2. Verify sort persistence across refreshes
3. Test zero-quantity filtering
4. Verify sold-out items are removed

## Files to Modify
- `modules/ebay_api.py` - Capture quantity from API
- `database/models.py` - Add quantity_available column
- `modules/deal_scanner.py` - Filter zero-quantity deals
- `templates/index.html` - Add sort buttons to headers
- `static/js/app.js` - Implement sorting logic
- `app.py` - Migration endpoint for new column