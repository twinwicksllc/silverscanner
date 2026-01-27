"""
SuperNinja Silver Deal Scanner - Main Flask Application
Web interface and API endpoints
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging
from datetime import datetime, timedelta
import threading

# Initialize Flask app FIRST
app = Flask(__name__)

# Configure logging AFTER Flask initialization
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import configuration and modules AFTER logging is configured
from config import Config
app.config.from_object(Config)

from modules.spot_price import SilverSpotPrice
from modules.ebay_api import eBayAPI
from modules.deal_scanner import DealScanner
from modules.scheduler import DigestScheduler
from database.models import DatabaseManager

# Custom filter for timeago
def timeago_filter(date_string):
    """Convert datetime string to 'X time ago' format"""
    if not date_string:
        return 'Never'
    
    try:
        date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        now = datetime.now(date.tzinfo)
        diff = now - date
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            return f'{int(seconds // 60)} minute{"" if int(seconds // 60) == 1 else "s"} ago'
        elif seconds < 86400:
            return f'{int(seconds // 3600)} hour{"" if int(seconds // 3600) == 1 else "s"} ago'
        elif seconds < 604800:
            return f'{int(seconds // 86400)} day{"" if int(seconds // 86400) == 1 else "s"} ago'
        else:
            return f'{int(seconds // 604800)} week{"" if int(seconds // 604800) == 1 else "s"} ago'
    except:
        return 'Unknown'

app.jinja_env.filters['timeago'] = timeago_filter

# Initialize components
try:
    spot_price = SilverSpotPrice()
    deal_scanner = DealScanner()
    db_manager = DatabaseManager()
    digest_scheduler = DigestScheduler()
    logger.info("All components initialized successfully")
except Exception as e:
    logger.error(f"Error initializing components: {e}")

# Global scan state
scan_state = {
    'last_scan_time': None,
    'is_scanning': False,
    'scan_results': [],
    'scan_error': None
}

@app.route('/healthz')
def health_check():
    """Health check endpoint for Render and other monitoring services"""
    return {"status": "healthy"}, 200

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get current price info
        price_info = spot_price.get_price_info()
        
        # Get recent deals from database
        recent_deals = db_manager.get_recent_deals(limit=20)
        
        # Get scan state
        last_scan = scan_state['last_scan_time']
        is_scanning = scan_state['is_scanning']
        
        return render_template('index.html',
                             price_info=price_info,
                             recent_deals=recent_deals,
                             last_scan=last_scan,
                             is_scanning=is_scanning,
                             scan_error=scan_state['scan_error'])
    
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('index.html',
                             error=str(e))

@app.route('/api/price')
def api_price():
    """API endpoint for current spot price"""
    try:
        price_info = spot_price.get_price_info()
        return jsonify({
            'success': True,
            'data': price_info
        })
    except Exception as e:
        logger.error(f"Error getting price info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _perform_scan_background():
    """Background thread function to perform scan"""
    global scan_state
    
    try:
        logger.info("Background scan started")
        
        # Perform scan
        deals = deal_scanner.perform_scan()
        
        # Save deals to database
        saved_count = 0
        for deal in deals:
            if db_manager.save_deal(deal):
                saved_count += 1
        
        # Save scan history
        summary = deal_scanner.get_deal_summary()
        scan_id = summary.get('scan_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        db_manager.save_scan_history({
            'scan_id': scan_id,
            'spot_price': summary.get('spot_price', 0),
            'threshold': summary.get('threshold', 0),
            'total_listings': len(deals) + summary.get('total_deals', 0),
            'total_deals': summary.get('total_deals', 0),
            'items_rejected': 0,
            'best_discount': summary.get('best_discount', 0),
            'avg_discount': summary.get('avg_discount', 0),
            'total_savings': summary.get('total_savings', 0),
            'status': 'completed'
        })
        
        # Update scan state
        scan_state['last_scan_time'] = datetime.now().isoformat()
        scan_state['scan_results'] = deal_scanner.get_all_formatted_deals()
        scan_state['items_scanned'] = len(deals) + summary.get('total_deals', 0)
        scan_state['deals_found'] = len(deals)
        scan_state['is_scanning'] = False
        
        logger.info(f"Background scan complete: {len(deals)} deals found, {saved_count} saved to database")
        
    except Exception as e:
        logger.error(f"Error during background scan: {e}")
        scan_state['is_scanning'] = False
        scan_state['scan_error'] = str(e)

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to trigger a scan (runs in background thread)"""
    global scan_state
    
    if scan_state['is_scanning']:
        return jsonify({
            'success': False,
            'error': 'Scan already in progress'
        }), 400
    
    try:
        scan_state['is_scanning'] = True
        scan_state['scan_error'] = None
        scan_state['items_scanned'] = 0
        scan_state['deals_found'] = 0
        
        logger.info("Manual scan triggered via API - starting background thread")
        
        # Start scan in background thread
        scan_thread = threading.Thread(target=_perform_scan_background, daemon=True)
        scan_thread.start()
        
        # Return immediately
        return jsonify({
            'success': True,
            'message': 'Scan started in background',
            'status': 'scanning'
        })
    
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        scan_state['is_scanning'] = False
        scan_state['scan_error'] = str(e)
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/deals')
def api_deals():
    """API endpoint to get deals"""
    try:
        limit = request.args.get('limit', 50, type=int)
        deals = db_manager.get_recent_deals(limit=limit)
        
        return jsonify({
            'success': True,
            'data': deals
        })
    except Exception as e:
        logger.error(f"Error getting deals: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scan/status')
def api_scan_status():
    """API endpoint to get scan status"""
    return jsonify({
        'success': True,
        'data': {
            'is_scanning': scan_state['is_scanning'],
            'last_scan_time': scan_state['last_scan_time'],
            'scan_error': scan_state['scan_error'],
            'items_scanned': scan_state.get('items_scanned', 0),
            'deals_found': scan_state.get('deals_found', 0),
            'recent_deals_count': len(scan_state['scan_results'])
        }
    })

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', config=Config)

@app.route('/api/settings', methods=['POST'])
def api_settings():
    """API endpoint to update settings"""
    try:
        data = request.json
        
        # Update configuration
        if 'threshold_percentage' in data:
            Config.DEAL_THRESHOLD_PERCENTAGE = float(data['threshold_percentage'])
        if 'scan_interval' in data:
            Config.SCAN_INTERVAL_MINUTES = int(data['scan_interval'])
        if 'min_seller_feedback' in data:
            Config.MIN_SELLER_FEEDBACK = float(data['min_seller_feedback'])
        
        logger.info("Settings updated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/price/history')
def api_price_history():
    """API endpoint to get silver spot price history"""
    try:
        days = request.args.get('days', 30, type=int)
        price_history = db_manager.get_price_history(days=days)
        
        return jsonify({
            'success': True,
            'data': price_history,
            'count': len(price_history)
        })
    except Exception as e:
        logger.error(f"Error fetching price history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test/eBay')
def api_test_ebay():
    """API endpoint to test eBay connection"""
    try:
        ebay_api = eBayAPI()
        success = ebay_api.test_connection()
        
        return jsonify({
            'success': success,
            'message': 'eBay API connection successful' if success else 'eBay API connection failed'
        })
    
    except Exception as e:
        logger.error(f"Error testing eBay connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create required directories
    import os
    os.makedirs(Config.LOG_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        logger.warning("Configuration validation warnings:")
        for error in config_errors:
            logger.warning(f"  - {error}")
    
    # Start digest scheduler
    try:
        digest_scheduler.start()
        logger.info("Digest scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start digest scheduler: {e}")
    
    # Run the app
    logger.info(f"Starting SuperNinja Silver Deal Scanner on port {Config.PORT}")
    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    finally:
        # Stop scheduler on shutdown
        try:
            digest_scheduler.stop()
        except:
            pass