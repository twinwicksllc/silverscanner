# 📋 eBay Developer Account Setup Guide

## Overview

Getting eBay API credentials requires several steps due to their compliance requirements. This guide walks you through the entire process.

## Step 1: Create eBay Developer Account

### 1.1 Register

1. Go to https://developer.ebay.com/
2. Click **"Sign Up"** in the top right
3. Fill in the registration form:
   - **Email Address**: Use a valid email you can access
   - **Password**: Create a strong password
   - **Name**: Your real name
   - **Country**: Select your country
4. Agree to terms and click **"Create Account"**

### 1.2 Verify Email

Check your email and click the verification link from eBay.

## Step 2: Complete Developer Profile

After logging in, you'll need to complete your profile:

1. **Developer Account Information**
   - **Company Name**: Can use your personal name
   - **Website**: Use `http://localhost:5000` (we're building a local app)
   - **Application Type**: Select **"Public"**
   - **Application Description**: 
     ```
     Silver Deal Scanner - Tool to help users find undervalued 
     silver coins and bullion on eBay by comparing listing prices 
     to current spot market prices.
     ```
   - **Category**: Select **"Shopping"** or **"Finance"**

2. **Contact Information**
   - Provide your contact details
   - Use your real email and phone number

## Step 3: Create an Application

### 3.1 Navigate to Application Management

1. After completing profile, go to **"My Account"** → **"Developer Account"**
2. Click **"Add a new application"**

### 3.2 Application Details

Fill in the application form:

**Basic Information:**
- **Application Name**: `SuperNinja Silver Scanner`
- **Application Type**: **Public** (important!)
- **Application Tier**: Start with **Sandbox** for testing, then switch to **Production**

**API Capabilities:**
- Select **"Buy API"** - This is what we need for searching listings
- You may also want **"Sell API"** for future features

**Callback URL:**
- Leave blank for now (not needed for our use case)

**Application Description** (copy this):
```
This application searches eBay listings for silver coins and bullion
to help users identify deals priced below current market spot prices.
It uses the Browse API to search for "Buy It Now" listings and 
calculates the actual silver content based on coin type and purity.
The application does not modify any listings or make purchases.
```

**Use Case** (select one):
- **Shopping / Price Comparison** - most accurate for our use case

### 3.3 Agree to Terms

Read and agree to the eBay API License Agreement and User Agreement.

## Step 4: Get Your Credentials

Once your application is created:

1. **Find Your Keys**
   - On the application page, you'll see:
     - **Client ID (App ID)**: Copy this
     - **Client Secret (Cert ID)**: Copy this

2. **Save Them Securely**
   - Store these in a secure location
   - Never share them publicly
   - Don't commit to version control

3. **Test in Sandbox** (Optional but Recommended)
   - Start with Sandbox tier to test your integration
   - Once working, switch to Production

## Step 5: Verify Access

### 5.1 Test Your Credentials

1. Go to the **eBay API Explorer**: https://developer.ebay.com/api-docs/
2. Select **"Buy API"** → **"Browse"** → **"Search"**
3. Enter your Client ID
4. Try a simple search to verify access

### 5.2 Check Rate Limits

Note your rate limits:
- **Sandbox**: Higher limits for testing
- **Production**: Typically 5,000 requests/hour
- Monitor usage to avoid hitting limits

## Step 6: Configure Your App

### 6.1 Update .env File

Edit `/workspace/silver_scanner/.env`:

```bash
# eBay API Configuration
EBAY_CLIENT_ID=your-actual-client-id-here
EBAY_CLIENT_SECRET=your-actual-client-secret-here
```

Replace the placeholder values with your actual credentials.

### 6.2 Test Connection

Start your app and test the connection:

```bash
cd /workspace/silver_scanner
python app.py
```

Then:
1. Go to http://localhost:5000/settings
2. Scroll to "eBay API Configuration"
3. Click "🧪 Test eBay Connection"
4. You should see a success notification

## Important Compliance Notes

### Data Usage Requirements

eBay requires you to:

1. **Display Source Attribution**
   - Show that data comes from eBay
   - Our app does this via item links

2. **Respect Rate Limits**
   - Don't exceed your API limits
   - Our app has built-in rate limiting

3. **User Privacy**
   - Don't store personal user data
   - Our app only stores public listing data

4. **Terms of Use**
   - Don't use data for competing platforms
   - Don't circumvent eBay's buying process
   - Our app is for deal finding only

### Application Review Process

eBay may review your application:

- **Sandbox**: Usually automatic approval
- **Production**: May take 1-3 business days
- They may ask for:
  - More details about your use case
  - How you're using the data
  - Privacy policy (if collecting user data)
  - Terms of service

### Production Access Tips

To get Production access faster:

1. **Be Specific** in your application description
2. **Show Value** to eBay buyers/sellers
3. **Provide Examples** of how you'll use the API
4. **Start with Sandbox** to prove it works
5. **Respond Quickly** to any review questions

## Common Issues & Solutions

### Issue: Application Rejected

**Solution:**
- Review rejection reasons carefully
- Modify application description
- Resubmit with more details
- Contact eBay Developer Support

### Issue: Low Rate Limits

**Solution:**
- Start with Sandbox for testing
- Build trust by using API responsibly
- Request higher limits after showing consistent use
- Contact support explaining your use case

### Issue: OAuth Authentication Failed

**Solution:**
- Verify Client ID and Secret are correct
- Check for extra spaces or special characters
- Ensure application is in correct tier (Sandbox/Production)
- Make sure you're using the correct environment URLs

### Issue: Rate Limit Exceeded

**Solution:**
- Our app has built-in rate limiting
- Increase scan interval in settings
- Reduce items per scan
- Monitor API usage in eBay Developer Portal

## Timeline Expectations

### Best Case:
- Day 1: Create account and application
- Day 1-2: Sandbox access approved (automatic)
- Day 2-3: Testing in Sandbox
- Day 3-4: Apply for Production
- Day 5-7: Production access approved

### With Review:
- Day 1: Create account and application
- Day 2-3: Sandbox testing
- Day 3: Submit for Production
- Day 7-10: Production review and approval

### With Questions:
- Day 1: Create account
- Day 2-3: eBay requests more information
- Day 4-5: Provide additional details
- Day 7-14: Final approval

## Support Resources

### eBay Developer Support
- **Developer Forums**: https://developer.ebay.com/forums/
- **Contact Support**: https://developer.ebay.com/contact-us
- **API Documentation**: https://developer.ebay.com/api-docs/

### SuperNinja Support
- **Setup Guide**: SETUP_GUIDE.md
- **Quick Start**: QUICKSTART.md
- **Full Documentation**: README.md

## Security Best Practices

1. **Never Commit Credentials**
   - Keep `.env` out of version control
   - Use `.gitignore` to exclude it

2. **Rotate Secrets**
   - Change Client Secret periodically
   - Regenerate if compromised

3. **Monitor Usage**
   - Check API usage regularly
   - Look for unusual activity

4. **Use HTTPS**
   - Always use secure connections
   - Our app does this automatically

## Next Steps After Setup

1. **Test in Sandbox** (1-2 hours)
   - Verify all features work
   - Test search and filtering
   - Check deal detection

2. **Apply for Production** (5 minutes)
   - Submit application for review
   - Wait for approval

3. **Start Scanning** (After approval)
   - Configure scan frequency
   - Set up email alerts
   - Monitor for deals

---

## Summary Checklist

- [ ] Create eBay Developer Account
- [ ] Complete developer profile
- [ ] Create application (start with Sandbox)
- [ ] Copy Client ID and Client Secret
- [ ] Update .env file with credentials
- [ ] Test connection in Sandbox
- [ ] Verify rate limits
- [ ] Apply for Production access
- [ ] Wait for approval (1-3 business days)
- [ ] Update .env for Production URLs
- [ ] Test in Production
- [ ] Start scanning for deals!

---

**Need Help?**

If you encounter issues:
1. Check eBay Developer Forums
2. Review API documentation
3. Contact eBay Developer Support
4. Refer to this guide's troubleshooting section

**Estimated Time to Setup:**
- Account creation: 10 minutes
- Application setup: 15 minutes
- Sandbox testing: 1-2 hours
- Production approval: 1-3 business days

**Total: 1-4 days to be fully operational**

Good luck with your eBay API setup! 🚀