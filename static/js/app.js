/**
 * SuperNinja Silver Deal Scanner - JavaScript
 * Handles dynamic functionality and API interactions
 */

// Global state
const AppState = {
    isScanning: false,
    lastScanTime: null,
    priceInfo: null,
    deals: [],
    scanInterval: null,
    sortBy: 'discount',  // default sort: discount (highest first)
    sortOrder: 'desc',   // desc = descending, asc = ascending
    currentMetal: 'silver'  // current metal filter
};

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatPercentage(value) {
    return value.toFixed(1) + '%';
}

function formatDateTime(isoString) {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function timeSince(isoString) {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
        }
    }
    
    return 'Just now';
}

// API Functions
async function fetchPriceInfo(metalType = null) {
    console.log('fetchPriceInfo() called with metalType:', metalType);
    const metal = metalType || AppState.currentMetal || 'silver';
    
    try {
        const response = await fetch(`/api/price?metal_type=${metal}`);
        console.log('fetchPriceInfo response status:', response.status);
        const data = await response.json();
        console.log('fetchPriceInfo data:', data);
        
        if (data.success) {
            AppState.priceInfo = data.data;
            updatePriceDisplay();
        }
    } catch (error) {
        console.error('Error fetching price info:', error);
    }
}

async function fetchPriceHistory(metalType = null) {
    console.log('fetchPriceHistory() called with metalType:', metalType);
    const metal = metalType || AppState.currentMetal || 'silver';
    
    try {
        const response = await fetch(`/api/price/history?metal_type=${metal}&days=30`);
        console.log('fetchPriceHistory response status:', response.status);
        const data = await response.json();
        console.log('fetchPriceHistory data:', data);
        
        if (data.success) {
            updatePriceChart(data.data);
        }
    } catch (error) {
        console.error('Error fetching price history:', error);
    }
}

async function fetchScanStatus() {
    try {
        const response = await fetch('/api/scan/status');
        const data = await response.json();
        
        if (data.success) {
            AppState.isScanning = data.is_scanning;
            AppState.lastScanTime = data.last_scan_time;
            updateScanStatus();
        }
    } catch (error) {
        console.error('Error fetching scan status:', error);
    }
}

async function fetchDeals(metalType = null) {
    console.log('fetchDeals() called with metalType:', metalType);
    
    // Use provided metalType or current filter
    const metal = metalType || AppState.currentMetal || 'silver';
    try {
        const response = await fetch(`/api/deals?limit=50&amp;metal_type=${metal}`);
        console.log('fetchDeals response status:', response.status);
        const data = await response.json();
        console.log('fetchDeals data:', data);
        
        if (data.success) {
            AppState.deals = data.data;
            updateDealsTable();
        }
    } catch (error) {
        console.error('Error fetching deals:', error);
    }
}

async function startScan() {
    console.log('startScan() called, isScanning:', AppState.isScanning);
    if (AppState.isScanning) {
        console.log('Scan already in progress, ignoring click');
        return;
    }
    
    try {
        AppState.isScanning = true;
        updateScanStatus();
        updateScanButton();
        
        console.log('Sending POST request to /api/scan');
        const metalType = AppState.currentMetal || 'silver';
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ metal_type: metalType })
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            console.log('Scan started successfully, polling for completion');
            // Poll for scan completion
            await pollForScanComplete();
            
            // Refresh scan status after scan completes
            await fetchScanStatus();
            
            // Get the actual deals count from the latest scan
            const scanStatus = await fetch('/api/scan/status');
            const scanData = await scanStatus.json();
            const dealsFound = scanData.deals_found || AppState.deals.length;
            
            showNotification(
                `Scan complete! Found ${dealsFound} deals`,
                'success'
            );
        } else {
            console.error('Scan failed:', data.error);
            showNotification(`Scan failed: ${data.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error starting scan:', error);
        showNotification('Scan failed. Please try again.', 'error');
    } finally {
        AppState.isScanning = false;
        updateScanStatus();
        updateScanButton();
    }
}

async function pollForScanComplete() {
    // Wait 1 second before starting to poll (give backend time to set is_scanning flag)
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Poll scan status every 2 seconds until scanning is complete
    const maxPolls = 60; // Max 2 minutes of polling
    let pollCount = 0;
    
    while (pollCount < maxPolls) {
        try {
            const response = await fetch('/api/scan/status');
            const data = await response.json();
            
            if (data.success) {
                // Update live counter with elapsed time
                if (data.items_scanned !== undefined) {
                    const itemsScannedEl = document.getElementById('items-scanned');
                    if (itemsScannedEl) {
                        const elapsed = data.elapsed_time || 0;
                        itemsScannedEl.textContent = `${elapsed}s ${data.items_scanned} items checked`;
                    }
                }
                
                if (!data.is_scanning) {
                    // Scan is complete
                    
                    // Auto-refresh dashboard
                    await fetchDeals();
                    await fetchPriceInfo();
                    
                    // UI State Reset - after all updates complete
                    AppState.isScanning = false;
                    updateScanButton();
                    
                    return;
                }
            }
        } catch (error) {
            console.error('Error polling scan status:', error);
        }
        
        pollCount++;
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

// UI Update Functions
function updatePriceDisplay() {
    const priceInfo = AppState.priceInfo;
    if (!priceInfo) return;
    
    // Update spot price - API returns 'spot_price'
    const spotPriceEl = document.getElementById('spot-price');
    if (spotPriceEl) {
        if (priceInfo.spot_price !== null && priceInfo.spot_price !== undefined) {
            spotPriceEl.textContent = formatCurrency(priceInfo.spot_price);
        } else {
            spotPriceEl.textContent = 'Loading...';
        }
    }
    
    // Update threshold - calculate from spot_price
    const thresholdEl = document.getElementById('threshold-price');
    if (thresholdEl && priceInfo.spot_price) {
        const thresholdPercent = 0.89; // 89% threshold from config
        const threshold = priceInfo.spot_price * thresholdPercent;
        thresholdEl.textContent = formatCurrency(threshold);
    }
    
    // Update last update - API returns 'timestamp' not 'last_update'
    const lastUpdateEl = document.getElementById('last-price-update');
    if (lastUpdateEl && priceInfo.timestamp) {
        lastUpdateEl.textContent = `Updated ${timeSince(priceInfo.timestamp)}`;
    }
}

function updateScanStatus() {
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const lastScanEl = document.getElementById('last-scan-time');
    const itemsScannedEl = document.getElementById('items-scanned');
    
    if (statusIndicator) {
        statusIndicator.className = 'status-indicator';
        if (AppState.isScanning) {
            statusIndicator.classList.add('scanning');
        }
    }
    
    if (statusText) {
        if (AppState.isScanning) {
            statusText.textContent = 'Scanning eBay for deals...';
        } else if (AppState.lastScanTime) {
            statusText.textContent = `Finished ${timeSince(AppState.lastScanTime)}`;
        } else {
            statusText.textContent = 'Ready to scan';
        }
    }
    
    if (lastScanEl) {
        if (AppState.lastScanTime) {
            lastScanEl.textContent = `Last scan: ${timeSince(AppState.lastScanTime)}`;
        } else {
            lastScanEl.textContent = 'Last scan: Never';
        }
    }
    
    if (itemsScannedEl) {
        // Only reset during non-scanning states
        // During scanning, pollForScanComplete will update this in real-time
        if (!AppState.isScanning) {
            itemsScannedEl.textContent = 'Ready';
        }
    }
    
    updateScanButton();
}

function updateScanButton() {
    const scanButton = document.getElementById('scan-button');
    if (scanButton) {
        scanButton.disabled = AppState.isScanning;
        scanButton.innerHTML = AppState.isScanning 
            ? '<span class="loading"></span> Scanning...' 
            : '🔍 Start Scan';
    }
}

function sortDeals(deals) {
    const sorted = [...deals];
    
    sorted.sort((a, b) => {
        let compareValue = 0;
        
        switch (AppState.sortBy) {
            case 'discount':
                // Sort by discount percentage
                compareValue = b.discount_percent - a.discount_percent;
                break;
            case 'price_per_oz':
                // Sort by cost per ounce (lower is better)
                compareValue = a.cost_per_oz - b.cost_per_oz;
                break;
            case 'time_listed':
                // Sort by time listed (newer first)
                const timeA = a.time_listed ? new Date(a.time_listed).getTime() : 0;
                const timeB = b.time_listed ? new Date(b.time_listed).getTime() : 0;
                compareValue = timeB - timeA;
                break;
        }
        
        // Reverse if ascending order
        return AppState.sortOrder === 'asc' ? -compareValue : compareValue;
    });
    
    return sorted;
}

function updateDealsTable() {
    const dealsTable = document.getElementById('deals-table-body');
    const emptyState = document.getElementById('empty-state');
    const dealsSection = document.getElementById('deals-section');
    
    if (!dealsTable) return;
    
    // Clear existing rows
    dealsTable.innerHTML = '';
    
    if (AppState.deals.length === 0) {
        // Show empty state
        if (emptyState) {
            emptyState.style.display = 'block';
        }
        if (dealsSection) {
            dealsSection.style.display = 'none';
        }
        return;
    }
    
    // Show deals section
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    if (dealsSection) {
        dealsSection.style.display = 'block';
    }
    
    // Sort deals before rendering
    const sortedDeals = sortDeals(AppState.deals);
    
    // Populate table
    sortedDeals.forEach(deal => {
        const row = document.createElement('tr');
        
        // Determine discount badge class
        let discountClass = 'low';
        if (deal.discount_percent > 15) {
            discountClass = 'high';
        } else if (deal.discount_percent > 10) {
            discountClass = 'medium';
        }
        
        // Determine seller rating class
        let ratingClass = 'good';
        if (deal.seller_feedback >= 99.5) {
            ratingClass = 'excellent';
        }
        
        row.innerHTML = `
            <td>
                <a href="${deal.item_url}" target="_blank" class="deal-link">
                    ${deal.title.substring(0, 60)}${deal.title.length > 60 ? '...' : ''}
                </a>
                <br>
                <small class="coin-type">${deal.coin_name}</small>
            </td>
            <td>
                <strong>${formatCurrency(deal.total_cost)}</strong>
                <br>
                <small>Item: ${formatCurrency(deal.price)} + Ship: ${formatCurrency(deal.shipping_cost)}</small>
            </td>
            <td>
                <strong>${deal.silver_weight_oz.toFixed(2)} oz</strong>
            </td>
            <td>
                <strong>${formatCurrency(deal.cost_per_oz)}/oz</strong>
                <br>
                <span class="discount-badge ${discountClass}">
                    ${formatPercentage(deal.discount_percent)} off
                </span>
            </td>
            <td>
                <div class="seller-rating ${ratingClass}">
                    ★ ${deal.seller_feedback.toFixed(1)}%
                </div>
                <small>${deal.seller_username}</small>
            </td>
            <td>
                ${deal.condition_tags && deal.condition_tags.length > 0 ? deal.condition_tags.slice(0, 2).join(' | ') : deal.condition}
                <br>
                <small>Listed ${deal.time_since_listed || 'Unknown'}</small>
            </td>
        `;
        
        dealsTable.appendChild(row);
    });
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        color: white;
        border-radius: 6px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Time formatting helper
function updateTimeAgo() {
    const priceTime = document.getElementById('price-time-ago');
    const scanTime = document.getElementById('scan-time-ago');
    
    if (priceTime && AppState.priceInfo && AppState.priceInfo.timestamp) {
        priceTime.textContent = timeSince(AppState.priceInfo.timestamp);
    }
    
    if (scanTime && AppState.lastScanTime) {
        scanTime.textContent = timeSince(AppState.lastScanTime);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize app
    fetchPriceInfo();
    fetchScanStatus();
    fetchDeals();
    
    // Set up periodic updates
    // setInterval(fetchPriceInfo, 30000); // REMOVED - Price only updates on scan
    setInterval(fetchScanStatus, 15000); // Update scan status every 15 seconds
    setInterval(fetchDeals, 60000); // Update deals every minute
    setInterval(updateTimeAgo, 1000); // Update timeago displays every second
    
    // Scan button
    const scanButton = document.getElementById('scan-button');
    if (scanButton) {
        scanButton.addEventListener('click', startScan);
    }
    
    // Settings form
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const settings = {
                threshold_percentage: formData.get('threshold_percentage'),
                scan_interval: formData.get('scan_interval'),
                min_seller_feedback: formData.get('min_seller_feedback'),
                user_timezone: formData.get('user_timezone')
            };
            
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(settings)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification('Settings updated successfully!', 'success');
                } else {
                    showNotification('Failed to update settings', 'error');
                }
            } catch (error) {
                showNotification('Error updating settings', 'error');
            }
        });
    }
    
    // Test eBay connection
    const testEbayButton = document.getElementById('test-ebay-button');
    if (testEbayButton) {
        testEbayButton.addEventListener('click', async function() {
            try {
                const response = await fetch('/api/test/eBay');
                const data = await response.json();
                
                if (data.success) {
                    showNotification('eBay API connection successful!', 'success');
                } else {
                    showNotification('eBay API connection failed', 'error');
                }
            } catch (error) {
                showNotification('Error testing eBay connection', 'error');
            }
        });
    }
    
    // Sort button event listeners
    const sortButtons = document.querySelectorAll('.sort-btn');
    sortButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sortType = this.getAttribute('data-sort');
            
            // Toggle sort order if clicking same button
            if (AppState.sortBy === sortType) {
                AppState.sortOrder = AppState.sortOrder === 'desc' ? 'asc' : 'desc';
            } else {
                // New sort type - set default order
                AppState.sortBy = sortType;
                if (sortType === 'price_per_oz') {
                    AppState.sortOrder = 'asc';  // Lower price is better
                } else {
                    AppState.sortOrder = 'desc'; // Higher discount/newer time is better
                }
            }
            
            // Update button states
            sortButtons.forEach(btn => {
                btn.classList.remove('active', 'asc', 'desc');
            });
            this.classList.add('active', AppState.sortOrder);
            
            // Re-render table with new sort
            updateDealsTable();
            
            // Show notification
            const sortNames = {
                'discount': 'Discount %',
                'price_per_oz': 'Price per Ounce',
                'time_listed': 'Time Listed'
            };
            const orderText = AppState.sortOrder === 'asc' ? 'ascending' : 'descending';
            showNotification(`Sorted by ${sortNames[sortType]} (${orderText})`, 'info');
        });
    });
    
    // Set initial active sort button
    const defaultSortBtn = document.querySelector('.sort-btn[data-sort="discount"]');
    if (defaultSortBtn) {
        defaultSortBtn.classList.add('active', 'desc');
    }
});

// Filter by metal type
function filterByMetal() {
    const metalFilter = document.getElementById('metal-type-filter');
    const selectedMetal = metalFilter.value;
    
    console.log('Filtering by metal:', selectedMetal);
    AppState.currentMetal = selectedMetal;
    
    // Update UI labels
    updateMetalLabels(selectedMetal);
    
    // Fetch deals for selected metal
    fetchDeals(selectedMetal);
    
    // Update price info for selected metal
    fetchPriceInfo(selectedMetal);
    
    // Update price history chart for selected metal
    fetchPriceHistory(selectedMetal);
}

// Update metal-specific labels in UI
function updateMetalLabels(metalType) {
    const metalName = metalType === 'all' ? 'All Metals' : 
                      metalType.charAt(0).toUpperCase() + metalType.slice(1);
    
    // Update various labels
    const elements = {
        'metal-name': metalName,
        'chart-metal-name': metalName,
        'deals-metal-name': metalName
    };
    
    Object.entries(elements).forEach(([id, text]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    });
    
    // Update threshold subtext based on metal
    const thresholdSubtext = document.getElementById('threshold-subtext');
    if (thresholdSubtext) {
        if (metalType === 'gold') {
            thresholdSubtext.textContent = '85% of spot (15% discount)';
        } else if (metalType === 'silver') {
            thresholdSubtext.textContent = '83% of spot (17% discount)';
        } else {
            thresholdSubtext.textContent = 'Max price per troy oz to qualify';
        }
    }
}

// Fetch all spot prices at once (optional optimization)
async function fetchAllSpotPrices() {
    console.log('fetchAllSpotPrices() called');
    
    try {
        const response = await fetch('/api/spot_prices');
        console.log('fetchAllSpotPrices response status:', response.status);
        const data = await response.json();
        console.log('fetchAllSpotPrices data:', data);
        
        if (data.success) {
            // Store all prices in AppState for quick access
            AppState.allPrices = data.data;
            return data.data;
        }
    } catch (error) {
        console.error('Error fetching all spot prices:', error);
        return null;
    }
}