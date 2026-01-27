# Email Notification Setup Guide

## ✅ Current Status - FULLY IMPLEMENTED

Your application now has a **complete email notification system** with two types of alerts: 

## 🔥 Fire Alarm Alerts (Instant)
- **Trigger:** Any deal with ≥15% discount off spot price
- **Timing:** Sent immediately when discovered
- **Subject:** 🚨 [EXCEPTIONAL DEAL] - {Item_Name} at {Discount}% Off!
- **Content:** Beautiful HTML email with deal details, pricing breakdown, and direct eBay link

## 📊 Silver Digest (Scheduled)
- **Trigger:** All deals meeting 89% threshold (but not sent as fire alarms)
- **Timing:** Twice daily at 12:00 PM and 8:00 PM CST
- **Subject:** 📊 Silver Scanner Digest: {Count} New Deals Found
- **Content:** Summary table of all qualifying deals with statistics

### What's Implemented ✅
- ✅ Complete SMTP email sending module (`modules/notifications.py`)
- ✅ Beautiful HTML email templates for both alert types
- ✅ Integration with deal scanner for instant fire alarms
- ✅ Scheduled digest system using APScheduler
- ✅ Duplicate prevention (won't send same alert twice in 24 hours)
- ✅ Email tracking in database (AlertHistory table)
- ✅ Configuration validation and error handling

---

## 🚀 How to Enable Email Notifications

The system is fully implemented and ready to use. Just follow these steps:

### Step 1: Get Gmail App Password
If using Gmail (recommended), you need an app-specific password:

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Navigate to **Security** → **2-Step Verification** (must be enabled first)
3. Scroll down to **App passwords**
4. Click "Select app" → Choose "Mail"
5. Click "Select device" → Choose "Other (Custom name)"
6. Enter "Silver Scanner" as the custom name
7. Click "Generate"
8. **Copy the 16-character password** (you won't see it again!)

### Step 2: Set Environment Variables in Render

Go to your Render dashboard → Your service → Environment tab, and add:

```bash
ENABLE_EMAIL_NOTIFICATIONS=True
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
```

**Important Notes:**
- `SMTP_USERNAME` and `EMAIL_FROM` should be the same Gmail address
- `EMAIL_TO` is where you want to receive alerts (can be different)
- Use the 16-character app password, NOT your regular Gmail password

### Step 3: Redeploy Your Application

After setting the environment variables:
1. Trigger a manual deploy in Render, OR
2. Push any change to GitHub to trigger auto-deploy

### Step 4: Verify It's Working

Check your application logs in Render for:
```
INFO - Digest scheduler started successfully
INFO - Digest scheduler started - emails will be sent at 12:00 PM and 8:00 PM CST
```

When a deal is found with ≥15% discount, you'll see:
```
INFO - Fire alarm triggered for [deal name]
INFO - Fire alarm sent for [deal name]
```

---

## Required Environment Variables

If you choose Option 1 (Full Email Implementation), here are all the environment variables you need:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ENABLE_EMAIL_NOTIFICATIONS` | Yes | Turn email on/off | `True` |
| `SMTP_SERVER` | Yes | SMTP server address | `smtp.gmail.com` |
| `SMTP_PORT` | Yes | SMTP port | `587` (TLS) |
| `SMTP_USERNAME` | Yes | Your email address | `your@gmail.com` |
| `SMTP_PASSWORD` | Yes | App-specific password | `xyz-abc-def-123` |
| `EMAIL_FROM` | No | From address (defaults to username) | `your@gmail.com` |
| `EMAIL_TO` | Yes | Where to send alerts | `your@gmail.com` |

---

## Gmail-Specific Setup

### Prerequisites
1. **2-Step Verification must be enabled** on your Google account
2. Regular Gmail passwords won't work - you must use an App Password

### Creating an App Password
1. Go to https://myaccount.google.com/apppasswords
2. Sign in again if prompted
3. Select "Mail" from the app dropdown
4. Select "Other (Custom name)" from the device dropdown
5. Enter "Silver Scanner" as the custom name
6. Click "Generate"
7. Copy the 16-character password (use this for SMTP_PASSWORD)

### Common Gmail Issues
- **"Authentication failed"** → Make sure you're using an app password, not your regular password
- **"Connection refused"** → Check SMTP_PORT (should be 587 for TLS, 465 for SSL)
- **Emails going to spam** → Check SPF/DKIM settings if using a custom domain

---

## Other Email Providers

If you prefer not to use Gmail, here are settings for common providers:

### Outlook/Hotmail
```
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

### Yahoo Mail
```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

### Custom SMTP Provider
Most email hosting providers (Bluehost, GoDaddy, etc.) provide SMTP settings in their documentation.

---

## Implementation Example

Here's what the email sending code would look like (if you implement it):

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
import logging

logger = logging.getLogger(__name__)

def send_deal_alert(deals):
    """Send email notification when deals are found"""
    
    if not Config.ENABLE_EMAIL_NOTIFICATIONS:
        logger.info("Email notifications are disabled")
        return
    
    if not deals:
        logger.info("No deals to send")
        return
    
    # Create email
    msg = MIMEMultipart()
    msg['From'] = Config.EMAIL_FROM or Config.SMTP_USERNAME
    msg['To'] = Config.EMAIL_TO
    msg['Subject'] = f"🔥 {len(deals)} New Silver Deals Found!"
    
    # Create HTML body
    body = f"""
    <h2>🎯 Silver Deal Alerts!</h2>
    <p>Found {len(deals)} deals below {Config.DEAL_THRESHOLD_PERCENTAGE}% of spot price:</p>
    """
    
    for deal in deals:
        body += f"""
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
            <h3>{deal['title']}</h3>
            <p><strong>Price:</strong> ${deal['total_price']:.2f}</p>
            <p><strong>Silver Value:</strong> ${deal['silver_value']:.2f}</p>
            <p><strong>Discount:</strong> {deal['discount_percentage']:.1f}%</p>
            <p><a href="{deal['item_url']}">View on eBay</a></p>
        </div>
        """
    
    msg.attach(MIMEText(body, 'html'))
    
    # Send email
    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Successfully sent email alert for {len(deals)} deals")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
```

---

---

## 📧 Email Templates

### Fire Alarm Alert
Beautiful gradient header with "EXCEPTIONAL DEAL ALERT!" badge, includes:
- Deal title and discount percentage in large text
- Grid layout with 6 key metrics (price, cost/oz, silver weight, spot price, savings, coin type)
- Prominent "VIEW ON EBAY NOW" button
- Warning box explaining why the deal is exceptional
- Professional footer

### Silver Digest
Clean table layout with summary statistics, includes:
- Header with date/time and gradient background
- Summary cards showing total deals, average discount, best discount
- Sortable table with all deals (item, price, discount, action button)
- Professional footer with schedule information

---

## 🎯 Summary

**System Status:** ✅ Fully Implemented and Ready

**What You Get:**
- 🚨 Instant alerts for exceptional deals (≥15% off)
- 📊 Twice-daily digest of all qualifying deals
- 🎨 Beautiful HTML email templates
- 🔒 Duplicate prevention
- 📈 Email tracking and history

**To Enable:**
1. Get Gmail app password (5 minutes)
2. Set 7 environment variables in Render (2 minutes)
3. Redeploy application (automatic)
4. Start receiving alerts!