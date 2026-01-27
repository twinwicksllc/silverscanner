# 🚀 Quick Start Guide - SuperNinja Silver Deal Scanner

## ⚡ Get Running in 5 Minutes

### Step 1: Verify Installation ✅

```bash
cd /workspace/silver_scanner
python -c "from config import Config; print('✓ Ready to go!')"
```

### Step 2: Get eBay API Credentials 🔑

**This is the ONLY required step!**

1. Go to https://developer.ebay.com/
2. Click "Sign Up" (free account)
3. After logging in, go to "My Account" → "Developer Account"
4. Click "Add a new application"
5. Fill in:
   - **Application Name**: SuperNinja Silver Scanner
   - **Application Type**: Public
   - **Application Tier**: Production
6. Click "Submit"
7. Copy your **Client ID** and **Client Secret**

### Step 3: Configure the App ⚙️

Edit the `.env` file:

```bash
nano /workspace/silver_scanner/.env
```

Replace these lines with your actual eBay credentials:

```bash
EBAY_CLIENT_ID=your-actual-client-id-here
EBAY_CLIENT_SECRET=your-actual-client-secret-here
```

Save and exit (Ctrl+X, then Y, then Enter)

### Step 4: Run the Application 🎯

```bash
cd /workspace/silver_scanner
python app.py
```

You should see:

```
INFO:__main__:All components initialized successfully
INFO:__main__:Starting SuperNinja Silver Deal Scanner on port 5000
 * Running on http://0.0.0.0:5000
```

### Step 5: Access the Dashboard 🌐

The application is now running! You can access it at:
- **Local**: http://localhost:5000
- **SuperNinja**: The public URL will be automatically generated

## 📋 First-Time Setup Checklist

Once the dashboard loads:

- [ ] Spot price displays correctly
- [ ] Go to Settings → Test eBay Connection
- [ ] Configure your deal threshold (default: 83% is good)
- [ ] Click "Start Scan" on the dashboard
- [ ] Review any deals found

## 🎯 What Happens Next

1. **Scanner searches eBay** for silver listings
2. **Calculates actual silver content** from coin types
3. **Computes cost per ounce** including shipping
4. **Identifies deals** below your threshold
5. **Displays results** sorted by best discount

## ⚠️ Important Notes

### Deal Reality Check
- **Genuine sub-spot deals are RARE** - don't expect many results
- Most sellers update prices quickly during market volatility
- Be patient and persistent - this tool shines during rapid price movements

### Safety First
- Always verify seller feedback before purchasing
- Deals significantly below spot are often counterfeit
- Use PayPal for buyer protection
- Read descriptions carefully

### Rate Limits
- eBay API has limits (5,000 requests/hour)
- Don't scan too frequently (15 minutes minimum)
- The scanner respects these limits automatically

## 🆘 Troubleshooting

### "eBay API Authentication Failed"
- Check your Client ID and Secret in `.env`
- Make sure there are no extra spaces
- Verify your eBay app is in "Production" mode

### "No Deals Found"
- This is normal! Deals are scarce
- Try lowering the threshold (e.g., 85% instead of 83%)
- Check that keywords are matching listings

### Port Already in Use
```bash
pkill -f "python app.py"
python app.py
```

## 📚 Learn More

- **Full Documentation**: See `README.md`
- **Detailed Setup**: See `SETUP_GUIDE.md`
- **Configuration**: See `.env` file

## 🎉 You're Ready!

Your SuperNinja Silver Deal Scanner is now hunting for undervalued silver deals on eBay. 

**Happy Deal Hunting! 🥈💰**

---

**Need Help?**
- Check the logs: `tail -f /workspace/silver_scanner/logs/silver_scanner.log`
- Review configuration in `.env`
- Test eBay connection in Settings page