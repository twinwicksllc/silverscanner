"""
SuperNinja Silver Deal Scanner - Configuration Module
Handles all application settings and environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration settings"""
    
    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'silver-scanner-secret-key-2024')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # eBay API Configuration
    EBAY_CLIENT_ID = os.getenv('EBAY_CLIENT_ID', '')
    EBAY_CLIENT_SECRET = os.getenv('EBAY_CLIENT_SECRET', '')
    EBAY_USE_SANDBOX = os.getenv('EBAY_USE_SANDBOX', 'True').lower() == 'true'
    
    # Set API URLs based on environment (Sandbox vs Production)
    if EBAY_USE_SANDBOX:
        EBAY_MARKETPLACE_ID = 'EBAY-US'
        EBAY_API_BASE_URL = 'https://api.sandbox.ebay.com/buy/browse/v1'
        EBAY_OAUTH_URL = 'https://api.sandbox.ebay.com/identity/v1/oauth2/token'
    else:
        EBAY_MARKETPLACE_ID = 'EBAY-US'
        EBAY_API_BASE_URL = 'https://api.ebay.com/buy/browse/v1'
        EBAY_OAUTH_URL = 'https://api.ebay.com/identity/v1/oauth2/token'
    
    # Scanning Configuration
    SCAN_INTERVAL_MINUTES = int(os.getenv('SCAN_INTERVAL_MINUTES', 15))
    MAX_ITEMS_PER_SCAN = int(os.getenv('MAX_ITEMS_PER_SCAN', 200))
    DEAL_THRESHOLD_PERCENTAGE = float(os.getenv('DEAL_THRESHOLD_PERCENTAGE', 83.0))
    MIN_SELLER_FEEDBACK = float(os.getenv('MIN_SELLER_FEEDBACK', 98.0))
    
    # Search Keywords and Categories
    SEARCH_KEYWORDS = [
        'Walking Liberty half',
        'Peace dollar',
        'Barber half',
        'junk silver',
        '90% silver',
        'Morgan dollar',
        'Constitutional silver',
        'Silver half dollars',
        'Silver dollars',
        '90% junk silver'
    ]
    
    EBAY_CATEGORY_COINS = '112862'  # Coins & Paper Money
    EBAY_CATEGORY_BULLION = '39487'  # Silver Bullion
    
    # Silver Spot Price Configuration
    SPOT_PRICE_SOURCES = [
        'https://www.jmbullion.com/charts/silver-prices/',
        'https://sdbullion.com/silver-prices',
        'https://www.apmex.com/spot/silver'
    ]
    SPOT_PRICE_CACHE_MINUTES = 15
    
    # Actual Silver Weight (ASW) Database
    # Troy ounces of pure silver in common U.S. coins
    ASW_VALUES = {
        # 90% Silver Coins
        'walking liberty half': 0.36169,
        'barber half': 0.36169,
        'franklin half': 0.36169,
        'kennedy half 1964': 0.36169,
        'peace dollar': 0.77344,
        'morgan dollar': 0.77344,
        'eisenhower dollar 1971-1976': 0.3161,
        
        # 40% Silver Coins
        'kennedy half 1965-1970': 0.1479,
        
        # Junk Silver (90% silver per $1 face value)
        'junk silver': 0.7234,  # per $1 face value
        'constitutional silver': 0.7234,  # per $1 face value
        '90% silver': 0.7234,  # per $1 face value
        
        # Bullion
        '1 oz silver round': 1.0,
        '1 oz silver bar': 1.0,
        '10 oz silver bar': 10.0,
        '100 oz silver bar': 100.0,
        'silver eagle': 1.0,
        'silver maple': 1.0,
        'silver britannia': 1.0,
    }
    
    # Database Configuration
    # Support both PostgreSQL (Supabase) and SQLite
    DATABASE_URL = os.getenv('DATABASE_URL', None)
    
    # If DATABASE_URL is not set, fall back to SQLite
    if not DATABASE_URL:
        DATABASE_PATH = os.path.join(
            os.environ.get('RENDER_PERSISTENT_DIR', 
                          os.path.join(os.path.dirname(__file__), 'database')), 
            'silver_scanner.db'
        )
        DATABASE_URL = f'sqlite:///{DATABASE_PATH}'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_PATH = os.path.join(os.path.dirname(__file__), 'logs')
    
    # Email Notification Settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', '')
    EMAIL_TO = os.getenv('EMAIL_TO', '')
    ENABLE_EMAIL_NOTIFICATIONS = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
    
    # Rate Limiting
    EBAY_API_RATE_LIMIT = 5000  # requests per hour
    API_CALL_DELAY_SECONDS = 0.72  # to stay within rate limits
    
    # Deal Scoring
    MIN_DEAL_CONFIDENCE = 0.6
    MAX_SHIPPING_COST = 20.0  # Maximum reasonable shipping cost
    
    @classmethod
    def validate(cls):
        """Validate required configuration settings"""
        errors = []
        
        if not cls.EBAY_CLIENT_ID:
            errors.append("EBAY_CLIENT_ID is required")
        if not cls.EBAY_CLIENT_SECRET:
            errors.append("EBAY_CLIENT_SECRET is required")
        if cls.ENABLE_EMAIL_NOTIFICATIONS:
            if not cls.SMTP_USERNAME:
                errors.append("SMTP_USERNAME is required when email notifications are enabled")
            if not cls.SMTP_PASSWORD:
                errors.append("SMTP_PASSWORD is required when email notifications are enabled")
            if not cls.EMAIL_TO:
                errors.append("EMAIL_TO is required when email notifications are enabled")
        
        return errors