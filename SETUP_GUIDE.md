# 🚀 SuperNinja Silver Deal Scanner - Setup Guide

This guide will walk you through setting up and running the SuperNinja Silver Deal Scanner in the SuperNinja environment.

## Prerequisites Check

Before starting, let's verify everything is ready:

```bash
# Check Python version (should be 3.8+)
python --version

# Check if pip is available
pip --version

# Verify we're in the correct directory
pwd
# Should show: /workspace/silver_scanner
```

## Step 1: Install Dependencies

First, install all required Python packages:

```bash
cd /workspace/silver_scanner
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Requests (HTTP client)
- BeautifulSoup (HTML parsing)
- SQLAlchemy (database)
- APScheduler (task scheduling)
- And other dependencies

## Step 2: Get eBay API Credentials

### 2.1 Create eBay Developer Account

1. Go to https://developer.ebay.com/
2. Click "Sign Up" (or "Sign In" if you already have an account)
3. Complete the registration process (free)

### 2.2 Create an Application

1. After logging in, go to "My Account" → "Developer Account"
2. Click "Add a new application"
3. Fill in the application details:
   - **Application Name**: SuperNinja Silver Scanner
   - **Application Type**: Public
   - **Notification Callback URL**: Leave blank
   - **Application Tier**: Production (or Sandbox for testing)
4. Agree to the terms and submit

### 2.3 Get Your Credentials

1. Once your application is created, you'll see:
   - **Client ID (App ID)**: Copy this
   - **Client Secret (Cert ID)**: Copy this
2. Keep these secure - you'll need them for the next step

## Step 3: Configure Environment Variables

### 3.1 Create .env File

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file
nano .env  # or use any text editor
```

### 3.2 Fill in Required Values

Edit `.env` and add your eBay credentials:

```bash
# eBay API Configuration (REQUIRED)
EBAY_CLIENT_ID=your-actual-client-id-here
EBAY_CLIENT_SECRET=your-actual-client-secret-here

# Flask Configuration
SECRET_KEY=change-this-to-a-random-string
DEBUG=True

# Deal Detection Settings
DEAL_THRESHOLD_PERCENTAGE=83.0
MIN_SELLER_FEEDBACK=98.0
SCAN_INTERVAL_MINUTES=15

# Email Notifications (OPTIONAL - leave as False for now)
ENABLE_EMAIL_NOTIFICATIONS=False
```

### 3.3 Important Notes

- **Never commit `.env` to version control** - it contains sensitive credentials
- Keep your eBay Client Secret secure
- The SECRET_KEY should be a random string for security

## Step 4: Initialize the Database

The database will be created automatically when you first run the app, but let's verify the setup:

```bash
# Create the database directory if it doesn't exist
mkdir -p /workspace/silver_scanner/database

# Create logs directory
mkdir -p /workspace/silver_scanner/logs
```

## Step 5: Test the Configuration

Let's verify everything is configured correctly:

```bash
# Test Python imports
python -c "from config import Config; print('Config loaded successfully')"

# Test eBay API connection (optional)
python -c "from modules.ebay_api import eBayAPI; api = eBayAPI(); print(api.test_connection())"
```

## Step 6: Run the Application

### Option A: Direct Python Execution

```bash
python app.py
```

### Option B: Using the Run Script

```bash
python run.py
```

You should see output like:

```
🥈 SuperNinja Silver Deal Scanner Starting...
==================================================
Dashboard will be available at: http://localhost:5000
Press Ctrl+C to stop the server
==================================================
 * Running on http://0.0.0.0:5000
```

## Step 7: Access the Dashboard

### 7.1 Expose the Port

Since we're running in SuperNinja, expose the port to access it from your browser:

```bash
# The port should be exposed automatically when app.py runs
# If not, you can expose it manually
```

### 7.2 Open in Browser

Navigate to the dashboard URL (shown when you run the app):
- http://localhost:5000
- Or the public URL provided by SuperNinja

## Step 8: Initial Configuration

### 8.1 Test eBay Connection

1. Go to the Settings page (click "Settings" in the navigation)
2. Scroll down to "eBay API Configuration"
3. Click "🧪 Test eBay Connection"
4. You should see a success notification

### 8.2 Configure Your Preferences

Adjust these settings based on your preferences:

**Deal Detection:**
- **Deal Threshold**: Start with 83% (can adjust later)
- **Minimum Seller Feedback**: 98.0% is recommended for safety

**Scanning:**
- **Scan Interval**: 15 minutes is good (don't go below 5 minutes)

### 8.3 Start Your First Scan

1. Go back to the Dashboard
2. Click "🔍 Start Scan"
3. Watch the scan progress
4. Review any deals found

## Step 9: Verify Everything Works

Checklist:

- [ ] Dashboard loads successfully
- [ ] Spot price displays correctly
- [ ] eBay connection test passes
- [ ] Scan completes without errors
- [ ] Deals (if any) display in the table
- [ ] Settings page loads and saves

## Troubleshooting

### Problem: Import Errors

```bash
# Solution: Make sure you're in the correct directory
cd /workspace/silver_scanner

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: eBay API Authentication Failed

```bash
# Solution: Verify your credentials
cat .env | grep EBAY

# Make sure there are no extra spaces or quotes
# Try regenerating your Client Secret in eBay Developer Portal
```

### Problem: Port Already in Use

```bash
# Solution: Kill any existing Python processes
pkill -f "python app.py"
pkill -f "python run.py"

# Or use a different port in .env
PORT=5001 python app.py
```

### Problem: Database Errors

```bash
# Solution: Remove the existing database and let it recreate
rm -f /workspace/silver_scanner/database/silver_scanner.db

# The database will be recreated on next run
```

### Problem: Spot Price Not Loading

```bash
# Solution: Check internet connection
ping google.com

# Check the logs for errors
cat /workspace/silver_scanner/logs/silver_scanner.log
```

## Advanced Configuration

### Enable Email Notifications

1. Edit `.env`:
```bash
ENABLE_EMAIL_NOTIFICATIONS=True
EMAIL_TO=your-email@example.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use app-specific password
```

2. Go to Settings page to configure email preferences

### Customize Search Keywords

Edit `config.py` to add or modify search keywords:

```python
SEARCH_KEYWORDS = [
    'Walking Liberty half',
    'Peace dollar',
    'Barber half',
    'junk silver',
    '90% silver',
    # Add your own keywords here
]
```

### Adjust ASW Values

Edit `ASW_VALUES` in `config.py` to add custom coin types:

```python
ASW_VALUES = {
    'your-custom-coin': 0.12345,  # ASW in troy ounces
}
```

## Running as a Background Service

To run the scanner continuously in the background:

```bash
# Using nohup (no hangup)
nohup python run.py > scanner.log 2>&1 &

# Check if it's running
ps aux | grep "python run.py"

# View logs
tail -f scanner.log

# Stop the service
pkill -f "python run.py"
```

## Next Steps

Now that your scanner is running:

1. **Monitor for deals**: Check the dashboard regularly
2. **Adjust settings**: Fine-tune thresholds based on results
3. **Set up alerts**: Configure email notifications for immediate alerts
4. **Learn the market**: Understand which coins and listings are most profitable
5. **Act fast**: When a deal appears, act quickly before others find it

## Support

If you encounter issues:

1. Check the logs: `/workspace/silver_scanner/logs/silver_scanner.log`
2. Review the README.md for detailed documentation
3. Verify all configuration settings in `.env`
4. Test eBay API connection in the Settings page

## Security Best Practices

- **Never share your `.env` file** or eBay credentials
- **Use strong, unique secrets** for SECRET_KEY
- **Keep dependencies updated**: `pip install --upgrade -r requirements.txt`
- **Monitor API usage** to stay within eBay rate limits
- **Regularly review seller feedback** before making purchases

---

**You're all set! 🎉**

Your SuperNinja Silver Deal Scanner is now ready to find undervalued silver deals on eBay. Happy deal hunting! 🥈💰