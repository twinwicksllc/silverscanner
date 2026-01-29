"""
SuperNinja Silver Deal Scanner - Main Flask Application
Web interface and API endpoints
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging
from datetime import datetime, timedelta

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
def healthz():
    """Health check endpoint for Render and load balancers"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get current price info from database (no live fetch)
        latest_price = db_manager.get_latest_price()
        price_info = None
        
        if latest_price:
            price_info = {
                'spot_price': latest_price.price,
                'source': latest_price.source,
                'last_update': latest_price.timestamp,
                'verified': True
            }
        
        # Get recent deals from database
        recent_deals = db_manager.get_recent_deals(limit=20)
        
        # Get scan state from database
        last_scan_record = db_manager.get_last_scan()
        last_scan = last_scan_record.start_time.isoformat() if last_scan_record else None
        is_scanning = scan_state['is_scanning']
        
        # Prepare scan details for display
        scan_details = None
        if last_scan_record:
            duration = None
            if last_scan_record.end_time and last_scan_record.start_time:
                duration_seconds = (last_scan_record.end_time - last_scan_record.start_time).total_seconds()
                duration = f"{duration_seconds:.0f}s"
            
            scan_details = {
                'items_scanned': last_scan_record.total_listings_scanned or 0,
                'duration': duration,
                'deals_found': last_scan_record.qualified_deals_found or 0
            }
        
        return render_template('index.html',
                             price_info=price_info,
                             recent_deals=recent_deals,
                             last_scan=last_scan,
                             scan_details=scan_details,
                             is_scanning=is_scanning,
                             scan_error=scan_state['scan_error'])
    
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('index.html',
                             error=str(e))

@app.route('/api/price')
def api_price():
    """API endpoint for current spot price - returns database record only"""
    try:
        # Get most recent price from database (no live fetch)
        latest_price = db_manager.get_latest_price()
        
        if latest_price:
            price_info = {
                'price': latest_price.price,
                'source': latest_price.source,
                'timestamp': latest_price.timestamp.isoformat() if latest_price.timestamp else None,
                'verified': True
            }
        else:
            # Fallback to cached price if no database record
            price_info = spot_price.get_price_info()
            price_info['verified'] = False
        
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

def run_background_scan():
    """Background thread function to perform scan"""
    global scan_state
    
    try:
        logger.info("Background scan started")
        scan_start = datetime.utcnow()
        
        # Fetch fresh spot price at the START of scan (only fetch when scanning)
        logger.info("Fetching fresh spot price for scan...")
        spot_price.get_price_info()
        logger.info("Spot price fetch complete")
        
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
        scan_end = datetime.utcnow()
        
        db_manager.save_scan_history({
            'scan_id': scan_id,
            'start_time': scan_start,
            'end_time': scan_end,
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
        scan_state['is_scanning'] = False
        
        logger.info(f"Background scan complete: {len(deals)} deals found, {saved_count} saved to database")
        
    except Exception as e:
        logger.error(f"Error during background scan: {e}")
        scan_state['is_scanning'] = False
        scan_state['scan_error'] = str(e)


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to trigger a scan - runs in background thread"""
    global scan_state
    
    if scan_state['is_scanning']:
        return jsonify({
            'success': False,
            'error': 'Scan already in progress'
        }), 400
    
    try:
        scan_state['is_scanning'] = True
        scan_state['scan_error'] = None
        
        logger.info("Manual scan triggered via API - starting background thread")
        
        # Start scan in background thread
        import threading
        scan_thread = threading.Thread(target=run_background_scan, daemon=True)
        scan_thread.start()
        
        # Return immediately without waiting for scan to complete
        return jsonify({
            'success': True,
            'message': 'Scan started in background',
            'data': {
                'status': 'running',
                'message': 'Scan is running in the background. Check status with /api/scan/status'
            }
        })
    
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        scan_state['is_scanning'] = False
        scan_state['scan_error'] = str(e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
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
    # Get last scan from database
    last_scan_record = db_manager.get_last_scan()
    last_scan_time = last_scan_record.start_time.isoformat() if last_scan_record else None
    
    return jsonify({
        'success': True,
        'data': {
            'is_scanning': scan_state['is_scanning'],
            'last_scan_time': last_scan_time,
            'scan_error': scan_state['scan_error'],
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
        
        # Update configuration in memory and persist to database
        if 'threshold_percentage' in data:
            value = float(data['threshold_percentage'])
            Config.DEAL_THRESHOLD_PERCENTAGE = value
            db_manager.save_setting('DEAL_THRESHOLD_PERCENTAGE', str(value))
            
        if 'scan_interval' in data:
            value = int(data['scan_interval'])
            Config.SCAN_INTERVAL_MINUTES = value
            db_manager.save_setting('SCAN_INTERVAL_MINUTES', str(value))
            
        if 'min_seller_feedback' in data:
            value = float(data['min_seller_feedback'])
            Config.MIN_SELLER_FEEDBACK = value
            db_manager.save_setting('MIN_SELLER_FEEDBACK', str(value))
            
        if 'user_timezone' in data:
            value = str(data['user_timezone'])
            Config.USER_TIMEZONE = value
            db_manager.save_setting('USER_TIMEZONE', value)
            logger.info(f"User timezone updated to: {Config.USER_TIMEZONE}")
        
        logger.info("Settings updated successfully and persisted to database")
        
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

@app.route('/admin/migrate/time_listed', methods=['POST'])
def run_migration():
    """
    Admin endpoint to add time_listed column to deals table
    This can be called on Render to update the database schema
    
    Usage:
    curl -X POST https://scanner.teckstart.com/admin/migrate/time_listed \
      -H "X-Migration-Key: teckstart_migrate_2025"
    """
    
    # Simple security check - require a secret key
    expected_key = os.getenv('MIGRATION_SECRET_KEY', 'teckstart_migrate_2025')
    provided_key = request.headers.get('X-Migration-Key')
    
    if provided_key != expected_key:
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        return jsonify({
            'success': False,
            'error': 'DATABASE_URL not configured'
        }), 500
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'deals' 
            AND column_name = 'time_listed';
            """
            
            result = conn.execute(text(check_sql))
            existing = result.fetchone()
            
            if existing:
                logger.info("Column time_listed already exists - skipping migration")
                return jsonify({
                    'success': True,
                    'message': 'Column time_listed already exists',
                    'action': 'skipped'
                })
            
            logger.info("Adding time_listed column to deals table...")
            
            # Add the column
            alter_sql = """
            ALTER TABLE deals 
            ADD COLUMN time_listed TIMESTAMP;
            """
            
            conn.execute(text(alter_sql))
            conn.commit()
            
            logger.info("Creating index on time_listed column...")
            
            # Create index
            index_sql = """
            CREATE INDEX idx_deals_time_listed 
            ON deals(time_listed);
            """
            
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception as e:
                if "already exists" not in str(e):
                    raise
            
            engine.dispose()
            
            logger.info("Migration completed successfully!")
            
            return jsonify({
                'success': True,
                'message': 'Successfully added time_listed column to deals table',
                'action': 'created'
            })
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template('500.html'), 500

def load_settings_from_database():
    """Load settings from database and update Config"""
    try:
        settings = db_manager.get_all_settings()
        
        if 'DEAL_THRESHOLD_PERCENTAGE' in settings:
            Config.DEAL_THRESHOLD_PERCENTAGE = float(settings['DEAL_THRESHOLD_PERCENTAGE'])
            logger.info(f"Loaded DEAL_THRESHOLD_PERCENTAGE: {Config.DEAL_THRESHOLD_PERCENTAGE}")
            
        if 'SCAN_INTERVAL_MINUTES' in settings:
            Config.SCAN_INTERVAL_MINUTES = int(settings['SCAN_INTERVAL_MINUTES'])
            logger.info(f"Loaded SCAN_INTERVAL_MINUTES: {Config.SCAN_INTERVAL_MINUTES}")
            
        if 'MIN_SELLER_FEEDBACK' in settings:
            Config.MIN_SELLER_FEEDBACK = float(settings['MIN_SELLER_FEEDBACK'])
            logger.info(f"Loaded MIN_SELLER_FEEDBACK: {Config.MIN_SELLER_FEEDBACK}")
            
        if 'USER_TIMEZONE' in settings:
            Config.USER_TIMEZONE = settings['USER_TIMEZONE']
            logger.info(f"Loaded USER_TIMEZONE: {Config.USER_TIMEZONE}")
            
        logger.info("Settings loaded from database successfully")
        
    except Exception as e:
        logger.warning(f"Could not load settings from database: {e}")
        logger.info("Using default configuration values")


if __name__ == '__main__':
    # Create required directories
    import os
    os.makedirs(Config.LOG_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    # Load settings from database
    load_settings_from_database()
    
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


    finally:
        # Stop scheduler on shutdown
        try:
            digest_scheduler.stop()
        except:
            pass