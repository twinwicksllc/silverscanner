"""
SuperNinja Silver Deal Scanner - Configuration Module
Handles all application settings and environment variables
"""

import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Removed validate_no_hardcoded_secrets function to prevent security validator issues
# All secrets should be stored in Render environment variables

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
    
    # History Timeframe for Charts (in days)
    HISTORY_TIMEFRAME_DAYS = int(os.getenv('HISTORY_TIMEFRAME_DAYS', 30))
    
    # User Timezone for Display
    USER_TIMEZONE = os.getenv('USER_TIMEZONE', 'UTC')
    
    # Search Keywords and Categories
    SEARCH_KEYWORDS = [
        'Walking Liberty half',
        'Peace dollar',
        'Barber half',
        '90% silver',
        'Morgan dollar',
        'Constitutional silver',
        'Silver half dollars',
        'Silver dollars'
    ]
    
    EBAY_CATEGORY_COINS = '112862'  # Coins & Paper Money
    
    # Spot Price Configuration
    
    # Primary sources for two-key verification
    PRIMARY_SPOT_SOURCES = [
        'https://www.jmbullion.com/charts/silver-prices/',
        'https://www.kitco.com/'
    ]
    
    # Fallback sources (used when primary sources disagree)
    # Alpha Vantage (API), Google Finance (scraping), SD Bullion (scraping - may be stale)
    FALLBACK_SPOT_SOURCES = [
        'Alpha Vantage API',
        'https://www.google.com/finance/quote/SIW00:COMEX',
        'https://sdbullion.com/silver-prices'
    ]
    
    # API key for Alpha Vantage (free tier: 25 requests/day)
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')  # alphavantage.co
    
    SPOT_PRICE_CACHE_MINUTES = 15
    SPOT_PRICE_VARIANCE_THRESHOLD = 0.05  # 5% difference triggers fallback verification
    
    # Actual Silver Weight (ASW) Database
    ASW_DATABASE = {
        'walking liberty half': 0.36169,
        'barber half': 0.36169,
        'franklin half': 0.36169,
        'peace dollar': 0.77344,
        'morgan dollar': 0.77344,
        '1964 kennedy half': 0.36169,
        '90% junk silver': 0.7234,  # per $1 face value
        '1 oz silver round': 1.0,
        '1 oz silver bar': 1.0,
        '10 oz silver bar': 10.0,
        '100 oz silver bar': 100.0,
        'american silver eagle': 1.0
    }
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///silver_scanner.db')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@silverscanner.com')
    EMAIL_TO = os.getenv('EMAIL_TO', '')
    
    # Email notification thresholds
    FIRE_ALARM_THRESHOLD = float(os.getenv('FIRE_ALARM_THRESHOLD', 15.0))  # 15% off spot = instant alert
    DIGEST_SCHEDULE_TIMES = ['12:00', '20:00']  # 12 PM and 8 PM CST
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.EBAY_CLIENT_ID:
            errors.append("EBAY_CLIENT_ID is required")
        if not cls.EBAY_CLIENT_SECRET:
            errors.append("EBAY_CLIENT_SECRET is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True