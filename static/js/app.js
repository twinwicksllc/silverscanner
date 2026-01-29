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
    scanDuration: null,
    itemsScanned: null
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
async function fetchPriceInfo() {
    try {
        const response = await fetch('/api/price');
        const data = await response.json();
        
        if (data.success) {
            AppState.priceInfo = data.data;
            updatePriceDisplay();
        }
    } catch (error) {
        console.error('Error fetching price info:', error);
    }
}

async function fetchScanStatus() {
    try {
        const response = await fetch('/api/scan/status');
        const data = await response.json();
        
        if (data.success) {
            AppState.isScanning = data.data.is_scanning;
            AppState.lastScanTime = data.data.last_scan_time;
            AppState.scanDuration = data.data.duration;
            AppState.itemsScanned = data.data.items_scanned;
            updateScanStatus();
        }
    } catch (error) {
        console.error('Error fetching scan status:', error);
    }
}

async function fetchDeals() {
    try {
        const response = await fetch('/api/deals?limit=50');
        const data = await response.json();
        
        if (data.success) {
            AppState.deals = data.data;
            updateDealsTable();
        }
    } catch (error) {
        console.error('Error fetching deals:', error);
    }
}

async function startScan() {
    if (AppState.isScanning) return;
    
    try {
        AppState.isScanning = true;
        updateScanStatus();
        updateScanButton();
        
        const response = await fetch('/api/scan', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Poll for scan status to get final results
            await pollForScanComplete();
            
            // Refresh data after scan completes
            await Promise.all([
                fetchScanStatus(),
                fetchPriceInfo(),
                fetchDeals()
            ]);
            
            showNotification(
                'Scan complete!',
                'success'
            );
        } else {
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

async function pollForScanComplete() {
    // Poll scan status every 2 seconds until scanning is complete
    const maxPolls = 60; // Max 2 minutes of polling
    let pollCount = 0;
    
    while (pollCount < maxPolls) {
        try {
            const response = await fetch('/api/scan/status');
            const data = await response.json();
            
            if (data.success && !data.data.is_scanning) {
                // Scan is complete
                return;
            }
        } catch (error) {
            console.error('Error polling scan status:', error);
        }
        
        pollCount++;
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
} maxPolls) {
        try {
            const response = await fetch('/api/scan/status');
            const data = await response.json();
            
            if (data.success && !data.data.is_scanning) {
                // Scan is complete
                return;
            }
        } catch (error) {
            console.error('Error polling scan status:', error);
        }
        
        // Wait 2 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
        pollCount++;
    }
    
    console.warn('Scan polling timeout reached');
}
}

// UI Update Functions
function updatePriceDisplay() {
    const priceInfo = AppState.priceInfo;
    if (!priceInfo) return;
    
    // Update spot price - API returns 'price' not 'spot_price'
    const spotPriceEl = document.getElementById('spot-price');
    if (spotPriceEl) {
        if (priceInfo.price !== null && priceInfo.price !== undefined) {
            spotPriceEl.textContent = formatCurrency(priceInfo.price);
        } else {
            spotPriceEl.textContent = 'Loading...';
        }
    }
    
    // Update threshold - calculate from price
    const thresholdEl = document.getElementById('threshold-price');
    if (thresholdEl && priceInfo.price) {
        const thresholdPercent = 0.89; // 89% threshold from config
        const threshold = priceInfo.price * thresholdPercent;
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
    const scanDurationEl = document.getElementById('scan-duration');
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
    
    if (scanDurationEl && !AppState.isScanning) {
        if (AppState.scanDuration) {
            scanDurationEl.textContent = AppState.scanDuration;
        } else {
            scanDurationEl.textContent = 'N/A';
        }
    }
    
    if (itemsScannedEl && !AppState.isScanning) {
        if (AppState.itemsScanned) {
            itemsScannedEl.textContent = `${AppState.itemsScanned} items checked`;
        } else {
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
    
    // Populate table
    AppState.deals.forEach(deal => {
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
                ${deal.condition}
                <br>
                <small>${formatDateTime(deal.qualified_at)}</small>
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
                    // Refresh price info to get updated threshold
                    await fetchPriceInfo();
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
});