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

# Load settings from database immediately after initialization
# This runs every time the app is imported (including by Gunicorn)
def load_settings_from_database_early():
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

load_settings_from_database_early()

# Global scan state
scan_state = {
    'last_scan_time': None,
    'is_scanning': False,
    'scan_results': [],
    'scan_error': None,
    'items_scanned': 0,
    'elapsed_time': 0,
    'scan_start_time': None
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
            threshold_value = latest_price.price * (Config.DEAL_THRESHOLD_PERCENTAGE / 100.0)
            price_info = {
                'spot_price': latest_price.price,
                'threshold': threshold_value,
                'threshold_percentage': Config.DEAL_THRESHOLD_PERCENTAGE,
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
                             scan_error=scan_state['scan_error'],
                             config=Config)
    
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('index.html',
                             error=str(e))

@app.route('/api/price')
def api_price():
    """API endpoint for current spot price - supports metal_type parameter
    
    Query parameters:
        metal_type: 'silver' (default) or 'gold'
    """
    try:
        metal_type = request.args.get('metal_type', 'silver')
        
        # If "all" is requested, redirect to /api/spot_prices
        if metal_type == 'all':
            return jsonify({
                'success': False,
                'error': 'Use /api/spot_prices to get all metal prices at once'
            }), 400
        
        # Validate metal_type
        if metal_type not in ['silver', 'gold']:
            return jsonify({
                'success': False,
                'error': 'Invalid metal_type. Must be "silver" or "gold"'
            }), 400
        
        # Get price info based on metal type
        from modules.multi_metal_spot_price import MultiMetalSpotPrice
        multi_spot = MultiMetalSpotPrice()
        
        if metal_type == 'gold':
            price_info = multi_spot.get_gold_price_info()
        else:
            price_info = multi_spot.get_silver_price_info()
        
        return jsonify({
            'success': True,
            'data': {
                'spot_price': price_info.get('spot_price'),
                'threshold': price_info.get('threshold'),
                'source': price_info.get('source'),
                'timestamp': price_info.get('timestamp'),
                'verified': price_info.get('verified', False),
                'metal_type': metal_type
            }
        })
    except Exception as e:
        logger.error(f"Error getting price info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/spot_prices')
def api_spot_prices():
    """API endpoint to get spot prices for all supported metals at once
    
    Returns prices for silver, gold, platinum, and palladium in a single call
    """
    try:
        from modules.multi_metal_spot_price import MultiMetalSpotPrice
        multi_spot = MultiMetalSpotPrice()
        
        # Get all spot prices
        all_prices = multi_spot.get_all_spot_prices()
        
        # Format response with thresholds
        result = {}
        
        for metal, price_data in all_prices.items():
            spot_price = price_data.get('spot_price')
            
            if spot_price:
                # Calculate threshold based on metal type
                if metal == 'gold':
                    threshold = spot_price * 0.85  # 15% discount
                elif metal == 'silver':
                    threshold = spot_price * 0.83  # 17% discount
                elif metal == 'platinum':
                    threshold = spot_price * 0.90  # 10% discount
                elif metal == 'palladium':
                    threshold = spot_price * 0.90  # 10% discount
                else:
                    threshold = spot_price * 0.85  # Default 15% discount
                
                result[metal] = {
                    'spot_price': spot_price,
                    'threshold': threshold,
                    'source': price_data.get('source'),
                    'timestamp': price_data.get('timestamp'),
                    'verified': price_data.get('verified', False)
                }
            else:
                result[metal] = {
                    'spot_price': None,
                    'threshold': None,
                    'source': 'None',
                    'timestamp': price_data.get('timestamp'),
                    'verified': False,
                    'error': 'Price not available'
                }
        
        return jsonify({
            'success': True,
            'data': result,
            'metals': list(result.keys())
        })
    
    except Exception as e:
        logger.error(f"Error getting spot prices: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_background_scan(metal_type: str = 'silver'):
    """Background thread function to perform scan
    
    Args:
        metal_type: Type of metal to scan for ('silver' or 'gold')
    """
    global scan_state
    scan_start = datetime.utcnow()
    scan_state['scan_start_time'] = scan_start
    scan_state['items_scanned'] = 0
    scan_state['elapsed_time'] = 0
    scan_state['scan_error'] = None
    scan_state['metal_type'] = metal_type

    try:
        logger.info(f"Background {metal_type} scan started")
        scan_state['is_scanning'] = True

        # Create a new DealScanner instance for this specific metal type
        # This ensures the correct calculator is initialized
        scanner = DealScanner(metal_type=metal_type)
        
        # Fetch fresh spot price at the START of scan (only fetch when scanning)
        logger.info(f"Fetching fresh {metal_type} spot price for scan...")
        if metal_type == 'gold':
            scanner.spot_price.get_gold_price_info()
        else:
            scanner.spot_price.get_silver_price_info()
        logger.info("Spot price fetch complete")

        # Perform scan with specified metal type
        deals = scanner.perform_scan()
        total_items_scanned = scanner.items_scanned

        # Save deals to database
        saved_count = 0
        for deal in deals:
            if db_manager.save_deal(deal):
                saved_count += 1

        # Save scan history
        summary = scanner.get_deal_summary()
        scan_id = summary.get('scan_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        scan_end = datetime.utcnow()

        db_manager.save_scan_history({
            'scan_id': scan_id,
            'start_time': scan_start,
            'end_time': scan_end,
            'spot_price': summary.get('spot_price', 0),
            'threshold': summary.get('threshold', 0),
            'total_listings': total_items_scanned,
            'total_deals': summary.get('total_deals', 0),
            'items_rejected': 0,
            'best_discount': summary.get('best_discount', 0),
            'avg_discount': summary.get('avg_discount', 0),
            'total_savings': summary.get('total_savings', 0),
            'status': 'completed'
        })

        # Update scan state
        scan_state['last_scan_time'] = datetime.now().isoformat()
        scan_state['scan_results'] = scanner.get_all_formatted_deals()
        scan_state['items_scanned'] = total_items_scanned
        logger.info(f"Background {metal_type} scan complete: {len(deals)} deals found, {saved_count} saved to database")

    except Exception as e:
        logger.error(f"Error during background scan: {e}")
        scan_state['scan_error'] = str(e)
    finally:
        if scan_start:
            scan_state['elapsed_time'] = int((datetime.utcnow() - scan_start).total_seconds())
        else:
            scan_state['elapsed_time'] = scan_state.get('elapsed_time', 0)
        scan_state['is_scanning'] = False
        scan_state['scan_start_time'] = None
        logger.info("Background scan flag cleared")


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to trigger a scan - runs in background thread
    Supports metal_type parameter: 'silver' (default) or 'gold'
    """
    global scan_state
    
    if scan_state['is_scanning']:
        return jsonify({
            'success': False,
            'error': 'Scan already in progress'
        }), 400
    
    try:
        scan_state['is_scanning'] = True
        scan_state['scan_error'] = None
        
        # Get metal type from request (default to silver)
        metal_type = request.json.get('metal_type', 'silver') if request.is_json else 'silver'
        
        if metal_type not in ['silver', 'gold']:
            return jsonify({
                'success': False,
                'error': 'Invalid metal_type. Must be "silver" or "gold"'
            }), 400
        
        logger.info(f"Manual {metal_type} scan triggered via API - starting background thread")
        
        # Start scan in background thread with metal type
        import threading
        scan_thread = threading.Thread(target=run_background_scan, args=(metal_type,), daemon=True)
        scan_thread.start()
        
        # Return immediately without waiting for scan to complete
        return jsonify({
            'success': True,
            'message': f'{metal_type.capitalize()} scan started in background',
            'data': {
                'status': 'running',
                'metal_type': metal_type,
                'message': f'{metal_type.capitalize()} scan is running in the background. Check status with /api/scan/status'
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

@app.route('/api/deals')
def api_deals():
    """API endpoint to get deals
    Supports filtering by metal_type parameter: 'silver', 'gold', or 'all' (default)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        metal_type = request.args.get('metal_type', 'all')
        
        # Validate metal_type
        if metal_type not in ['silver', 'gold', 'all']:
            return jsonify({
                'success': False,
                'error': 'Invalid metal_type. Must be "silver", "gold", or "all"'
            }), 400
        
        deals = db_manager.get_recent_deals(limit=limit, metal_type=metal_type)
        
        return jsonify({
            'success': True,
            'data': deals,
            'metal_type': metal_type,
            'count': len(deals)
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
    
    # Get scan metrics from last scan record
    deals_found = last_scan_record.qualified_deals_found if last_scan_record else 0
    items_scanned = last_scan_record.total_listings_scanned if last_scan_record else 0
    elapsed = scan_state['elapsed_time']
    
    # During active scan, use real-time values from scan_state
    if scan_state['is_scanning'] and scan_state['scan_start_time']:
        elapsed = int((datetime.utcnow() - scan_state['scan_start_time']).total_seconds())
        items_scanned = scan_state['items_scanned']
    
    return jsonify({
        'success': True,
        'is_scanning': scan_state['is_scanning'],
        'last_scan_time': last_scan_time,
        'scan_error': scan_state['scan_error'],
        'recent_deals_count': len(scan_state['scan_results']),
        'deals_found': deals_found,
        'items_scanned': items_scanned,
        'elapsed_time': elapsed
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
    """API endpoint to get spot price history for specified metal"""
    try:
        days = request.args.get('days', 30, type=int)
        metal_type = request.args.get('metal_type', 'silver').lower()
        
        # Validate metal_type
        if metal_type not in ['silver', 'gold']:
            return jsonify({
                'success': False,
                'error': 'Invalid metal_type. Must be "silver" or "gold"'
            }), 400
        
        price_history = db_manager.get_price_history(days=days, metal_type=metal_type)
        
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

@app.route('/admin/migrate/listing_tracking', methods=['POST'])
def migrate_listing_tracking():
    """
    Admin endpoint to add listing tracking columns to deals table
    Adds: item_end_date, last_seen_in_scan
    
    Usage:
    curl -X POST https://scanner.teckstart.com/admin/migrate/listing_tracking \
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
        
        migrations_run = []
        
        with engine.connect() as conn:
            # Migration 1: Add item_end_date column
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'deals' 
            AND column_name = 'item_end_date';
            """
            result = conn.execute(text(check_sql))
            if not result.fetchone():
                logger.info("Adding item_end_date column...")
                conn.execute(text("ALTER TABLE deals ADD COLUMN item_end_date TIMESTAMP;"))
                conn.commit()
                migrations_run.append('item_end_date')
            
            # Migration 2: Add last_seen_in_scan column
            check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'deals' 
            AND column_name = 'last_seen_in_scan';
            """
            result = conn.execute(text(check_sql))
            if not result.fetchone():
                logger.info("Adding last_seen_in_scan column...")
                conn.execute(text("ALTER TABLE deals ADD COLUMN last_seen_in_scan TIMESTAMP;"))
                conn.commit()
                migrations_run.append('last_seen_in_scan')
            
            # Create indexes
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_deals_item_end_date ON deals(item_end_date);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_deals_last_seen ON deals(last_seen_in_scan);"))
                conn.commit()
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Index creation warning: {e}")
            
            engine.dispose()
            
            if migrations_run:
                logger.info(f"Migration completed! Added columns: {migrations_run}")
                return jsonify({
                    'success': True,
                    'message': f'Successfully added columns: {migrations_run}',
                    'columns_added': migrations_run
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'All columns already exist',
                    'action': 'skipped'
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
@app.route('/admin/test/db', methods=['GET'])
def test_db_connection():
    """Test database connection"""
    try:
        from sqlalchemy import create_engine, text
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            return jsonify({
                'success': False,
                'error': 'DATABASE_URL not configured'
            }), 500
        
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();" if 'postgresql' in database_url else "SELECT sqlite_version();"))
            version = result.fetchone()
            
            return jsonify({
                'success': True,
                'database_type': 'PostgreSQL' if 'postgresql' in database_url else 'SQLite',
                'version': str(version[0]),
                'database_url_preview': database_url[:50] + '...'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/migrate/metal_support', methods=['POST'])
def migrate_metal_support():
    """
    Admin endpoint to add multi-metal support columns
    
    Usage:
    curl -X POST https://scanner.teckstart.com/admin/migrate/metal_support \
      -H "X-Migration-Key: teckstart_migrate_2025"
    """
    
    # Simple security check
    expected_key = os.getenv('MIGRATION_SECRET_KEY', 'teckstart_migrate_2025')
    provided_key = request.headers.get('X-Migration-Key')
    
    if provided_key != expected_key:
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401
    
    try:
        import sys
        import os
        from sqlalchemy import create_engine, text, inspect
        
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            return jsonify({
                'success': False,
                'error': 'DATABASE_URL not configured'
            }), 500
        
        engine = create_engine(database_url)
        is_postgres = 'postgresql' in database_url
        
        logger.info(f"Starting multi-metal migration (database type: {'PostgreSQL' if is_postgres else 'SQLite'})")
        
        with engine.connect() as conn:
            # Step 1: Add metal_type column
            try:
                conn.execute(text("ALTER TABLE deals ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'"))
                conn.commit()
                logger.info("Added metal_type column")
            except Exception as e:
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    raise
            
            # Step 2: Add metal_purity column
            try:
                conn.execute(text("ALTER TABLE deals ADD COLUMN metal_purity FLOAT DEFAULT 1.0"))
                conn.commit()
                logger.info("Added metal_purity column")
            except Exception as e:
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    raise
            
            # Step 3: Create index on metal_type
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_deals_metal_type ON deals(metal_type)"))
                conn.commit()
                logger.info("Created index on metal_type")
            except Exception:
                pass  # Index may already exist
            
            # Step 4: Create spot_prices table
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if 'spot_prices' not in tables:
                if is_postgres:
                    conn.execute(text("""
                        CREATE TABLE spot_prices (
                            id SERIAL PRIMARY KEY,
                            metal_type VARCHAR(20) NOT NULL,
                            price FLOAT NOT NULL,
                            source VARCHAR(100),
                            timestamp TIMESTAMP DEFAULT NOW(),
                            verified BOOLEAN DEFAULT FALSE
                        )
                    """))
                else:
                    conn.execute(text("""
                        CREATE TABLE spot_prices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            metal_type VARCHAR(20) NOT NULL,
                            price FLOAT NOT NULL,
                            source VARCHAR(100),
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            verified BOOLEAN DEFAULT 0
                        )
                    """))
                conn.commit()
                logger.info("Created spot_prices table")
            
            # Step 5: Create index on spot_prices
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_spot_prices_metal_timestamp ON spot_prices(metal_type, timestamp DESC)"))
                conn.commit()
                logger.info("Created index on spot_prices")
            except Exception:
                pass
            
            # Step 6: Update price_history table
            try:
                conn.execute(text("ALTER TABLE price_history ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'"))
                conn.commit()
                logger.info("Added metal_type to price_history")
            except Exception as e:
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    raise
            
            # Step 7: Create index on price_history
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_price_history_metal ON price_history(metal_type, timestamp DESC)"))
                conn.commit()
                logger.info("Created index on price_history")
            except Exception:
                pass
        
        logger.info("Multi-metal support migration completed successfully")
        
        return jsonify({
            'success': True,
            'message': 'Multi-metal support migration completed',
            'columns_added': ['metal_type', 'metal_purity'],
            'tables_created': ['spot_prices'],
            'indexes_created': ['idx_deals_metal_type', 'idx_spot_prices_metal_timestamp']
        })
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/migrate/price_history_metal_type', methods=['POST'])
def migrate_price_history_metal_type():
    """
    Admin endpoint to add metal_type column to price_history table
    
    Usage:
    curl -X POST https://scanner.teckstart.com/admin/migrate/price_history_metal_type \
      -H "X-Migration-Key: teckstart_migrate_2025"
    """
    
    # Simple security check
    expected_key = os.getenv('MIGRATION_SECRET_KEY', 'teckstart_migrate_2025')
    provided_key = request.headers.get('X-Migration-Key')
    
    if provided_key != expected_key:
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401
    
    try:
        from database.models import DatabaseManager
        
        db = DatabaseManager()
        session = db.get_session()
        
        logger.info("Starting price_history metal_type migration using DatabaseManager")
        
        # Step 1: Add metal_type column
        try:
            session.execute("ALTER TABLE price_history ADD COLUMN metal_type VARCHAR(20) DEFAULT 'silver'")
            session.commit()
            logger.info("Added metal_type column to price_history")
        except Exception as e:
            session.rollback()
            if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                raise
            logger.info("metal_type column already exists")
        
        # Step 2: Create index on metal_type
        try:
            session.execute("CREATE INDEX IF NOT EXISTS idx_price_history_metal_type ON price_history(metal_type)")
            session.commit()
            logger.info("Created index on price_history.metal_type")
        except Exception as e:
            session.rollback()
            if 'already exists' in str(e).lower():
                logger.info("Index already exists")
            else:
                raise
        
        # Step 3: Update existing records to have metal_type = 'silver'
        try:
            session.execute("UPDATE price_history SET metal_type = 'silver' WHERE metal_type IS NULL OR metal_type = ''")
            session.commit()
            logger.info("Updated existing price_history records")
        except Exception as e:
            session.rollback()
            logger.warning(f"Could not update existing records: {e}")
        
        # Step 4: Create composite index for (metal_type, timestamp)
        try:
            session.execute("CREATE INDEX IF NOT EXISTS idx_price_history_metal_timestamp ON price_history(metal_type, timestamp)")
            session.commit()
            logger.info("Created composite index on price_history(metal_type, timestamp)")
        except Exception as e:
            session.rollback()
            if 'already exists' in str(e).lower():
                logger.info("Composite index already exists")
            else:
                raise
        
        session.close()
        logger.info("Price history metal_type migration completed successfully")
        
        return jsonify({
            'success': True,
            'message': 'Price history metal_type migration completed',
            'columns_added': ['metal_type'],
            'indexes_created': ['idx_price_history_metal_type', 'idx_price_history_metal_timestamp']
        })
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

