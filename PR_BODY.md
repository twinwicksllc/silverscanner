## Overview
This PR implements two major dashboard enhancements requested by the user:

1. **Sortable Deals Table** - Users can now sort deals by discount %, price/oz, or time listed
2. **Zero-Quantity Deal Removal** - Automatically removes sold-out items from the dashboard

## Enhancement 1: Sortable Deals Table

### Features
- **Sort by Discount %**: Click 🔥 button (default: highest to lowest)
- **Sort by Price/oz**: Click ↕️ button (default: lowest to highest)
- **Sort by Time Listed**: Click 🕐 button (default: newest to oldest)

### User Experience
- Click any sort button to sort by that column
- Click again to reverse sort order
- Active button highlighted with visual indicator
- Arrow indicators show current direction (↑ ↓)
- Toast notification confirms sort action

### Technical Implementation
- JavaScript sorting in `static/js/app.js`
- Sort state in `AppState.sortBy` and `AppState.sortOrder`
- Sort buttons in table headers (`templates/index.html`)
- Button styles in `static/css/style.css`

## Enhancement 2: Zero-Quantity Deal Removal

### Features
- Captures `quantityAvailable` from eBay API
- Filters out items with 0 quantity during scan
- Removes zero-quantity deals from database after each scan
- Enhanced expunge routine checks quantity

### User Experience
- Sold-out items never appear in dashboard
- When user purchases last item(s), next scan removes it
- Database stays clean - no stale listings
- Only actionable deals shown

### Technical Implementation

#### eBay API (`modules/ebay_api.py`)
- Capture `quantityAvailable` from API response
- Filter out items with quantity = 0 immediately
- Include quantity in item details

#### Database (`database/models.py`)
- New column: `quantity_available` (INTEGER, default 1)
- New method: `remove_zero_quantity_deals()`
- Enhanced `expunge_stale_hidden_deals()` to check quantity

#### Scanner (`modules/deal_scanner.py`)
- Call `remove_zero_quantity_deals()` after each scan
- Log removed count

#### Migration (`app.py`)
- New endpoint: `/admin/migrate/quantity_available`
- Adds column with index to existing databases

## Files Modified
- `modules/ebay_api.py` - Capture and filter quantity
- `database/models.py` - Add column, removal method, enhanced expunge
- `modules/deal_scanner.py` - Call removal after scan
- `app.py` - Add migration endpoint
- `templates/index.html` - Add sort buttons
- `static/js/app.js` - Sorting logic and event handlers
- `static/css/style.css` - Sort button styles

## Documentation
- `ENHANCEMENTS_IMPLEMENTED.md` - Complete implementation guide
- `ENHANCEMENT_PLAN.md` - Planning document

## Testing Checklist
- [x] Sort by discount % works
- [x] Sort by price/oz works
- [x] Sort by time listed works
- [x] Sort order toggles correctly
- [x] Active button highlighted
- [x] eBay API captures quantity
- [x] Zero-quantity items filtered
- [x] Database removal method works
- [x] Migration endpoint created

## Deployment Steps
1. Merge this PR
2. Run migration endpoint
3. Verify column exists in Supabase
4. Test sorting on dashboard
5. Run scan and verify sold-out items removed

## Breaking Changes
None - fully backward compatible

## Benefits
- Better deal discovery through sorting
- Clean dashboard with only actionable deals
- Improved data accuracy
- Enhanced user experience