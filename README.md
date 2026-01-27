# 🥈 SuperNinja Silver Deal Scanner

An automated web application that scans eBay for undervalued silver coins and bullion, helping you find deals below spot price during market volatility.

## 🌟 Features

- **Automated Scanning**: Continuously monitors eBay "Buy It Now" listings for silver deals
- **Smart ASW Calculation**: Automatically identifies coin types and calculates Actual Silver Weight
- **Real-Time Spot Prices**: Live silver price updates from multiple sources
- **Deal Detection**: Identifies items priced below your target threshold (default: 83% of spot)
- **Seller Filtering**: Only shows deals from reputable sellers (≥98% feedback)
- **Web Dashboard**: Clean, intuitive interface for monitoring deals
- **Email Alerts**: Get notified instantly when qualifying deals are found
- **Historical Tracking**: Store and review all discovered deals

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- eBay Developer Account (free) - Get API credentials at https://developer.ebay.com/
- Git (optional, for cloning)

### Installation

1. **Navigate to the project directory**:
   ```bash
   cd silver_scanner
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your eBay API credentials
   ```

5. **Get eBay API Credentials**:
   - Go to https://developer.ebay.com/
   - Create a free account
   - Create a new application
   - Copy your Client ID and Client Secret to `.env`

6. **Run the application**:
   ```bash
   python app.py
   ```

7. **Access the dashboard**:
   Open your browser and navigate to: http://localhost:5000

## 📖 Usage

### Basic Workflow

1. **Start the Application**: Run `python app.py` to launch the web server
2. **Configure Settings**: Visit `/settings` to customize:
   - Deal threshold percentage (default: 83% of spot price)
   - Minimum seller feedback (default: 98%)
   - Scan frequency (default: every 15 minutes)
   - Email notification settings
3. **Test Connection**: Use the "Test eBay Connection" button in settings
4. **Start Scanning**: Click "Start Scan" on the dashboard or wait for automatic scans
5. **Review Deals**: Browse discovered deals sorted by discount percentage
6. **Act Fast**: Click deal links to view items on eBay before they're gone!

### Supported Coin Types

The scanner automatically identifies these coin types:

**90% Silver Coins:**
- Walking Liberty Half Dollars (0.36169 oz ASW)
- Barber Half Dollars (0.36169 oz ASW)
- Franklin Half Dollars (0.36169 oz ASW)
- 1964 Kennedy Half Dollars (0.36169 oz ASW)
- Peace Dollars (0.77344 oz ASW)
- Morgan Dollars (0.77344 oz ASW)

**Junk Silver:**
- 90% Constitutional Silver (0.7234 oz per $1 face value)

**Silver Bullion:**
- 1 oz Silver Rounds (1.0 oz ASW)
- 1 oz Silver Bars (1.0 oz ASW)
- 10 oz Silver Bars (10.0 oz ASW)
- American Silver Eagles (1.0 oz ASW)

### Understanding the Metrics

- **Spot Price**: Current market price of silver per troy ounce
- **Threshold**: Maximum price per ounce to qualify as a deal (83% of spot)
- **Cost per oz**: Total cost (item + shipping) divided by silver weight
- **Discount %**: How much below spot price the deal is
- **ASW**: Actual Silver Weight in troy ounces

## ⚙️ Configuration

### Environment Variables

Edit `.env` to configure:

```bash
# eBay API (Required)
EBAY_CLIENT_ID=your-client-id
EBAY_CLIENT_SECRET=your-client-secret

# Deal Detection
DEAL_THRESHOLD_PERCENTAGE=83.0    # 83% of spot price
MIN_SELLER_FEEDBACK=98.0         # Minimum seller rating
SCAN_INTERVAL_MINUTES=15          # Auto-scan frequency

# Notifications (Optional)
ENABLE_EMAIL_NOTIFICATIONS=True
EMAIL_TO=your-email@example.com
```

### Web Interface Settings

Visit `/settings` to configure:
- Deal threshold percentage
- Minimum seller feedback
- Scan interval
- Email notifications
- eBay API credentials

## 🏗️ Project Structure

```
silver_scanner/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── modules/
│   ├── spot_price.py     # Silver spot price fetcher
│   ├── ebay_api.py       # eBay API client
│   ├── asw_calculator.py # Silver content calculator
│   └── deal_scanner.py   # Main scanning logic
├── database/
│   └── models.py         # Database models
├── templates/
│   ├── index.html        # Dashboard template
│   └── settings.html     # Settings template
├── static/
│   ├── css/
│   │   └── style.css     # Stylesheet
│   └── js/
│       └── app.js        # JavaScript logic
└── database/
    └── silver_scanner.db # SQLite database (created automatically)
```

## 🔧 API Endpoints

### Public Endpoints

- `GET /` - Main dashboard
- `GET /settings` - Settings page

### API Endpoints

- `GET /api/price` - Get current silver spot price
- `POST /api/scan` - Trigger a manual scan
- `GET /api/deals` - Get recent deals
- `GET /api/scan/status` - Get current scan status
- `POST /api/settings` - Update settings
- `GET /api/test/eBay` - Test eBay API connection

## 🔍 How It Works

1. **Fetch Spot Price**: Gets live silver price from JM Bullion, SD Bullion, or APMEX
2. **Search eBay**: Uses eBay Browse API to find "Buy It Now" silver listings
3. **Extract Data**: Parses item title, price, shipping, and seller info
4. **Calculate ASW**: Identifies coin type and calculates actual silver weight
5. **Compute Metrics**: Calculates cost per ounce and discount from spot price
6. **Filter Deals**: Applies thresholds for price, seller rating, and condition
7. **Store Results**: Saves qualified deals to database
8. **Send Alerts**: Notifies you via email when deals are found

## ⚠️ Important Notes

### Security & Legitimacy

- **Verify Sellers**: Always check seller feedback and reviews before purchasing
- **Watch for Fakes**: Deals significantly below spot are often counterfeit
- **Use PayPal**: Always use PayPal for buyer protection
- **Read Descriptions**: Carefully review item descriptions and photos

### Rate Limiting

- eBay API has rate limits (typically 5,000 requests/hour)
- The scanner respects these limits with built-in delays
- Don't scan too frequently (minimum 5-minute intervals)

### Deal Scarcity

- Genuine sub-spot deals are **extremely rare**
- Most sellers update prices quickly during market volatility
- This tool is most valuable during rapid price movements
- Be patient and persistent

## 🐛 Troubleshooting

### eBay API Authentication Failed

- Verify your Client ID and Client Secret are correct
- Check that your eBay application is in "Production" mode
- Ensure you're using the correct marketplace (EBAY-US)

### No Deals Found

- This is normal! Genuine deals are rare
- Try lowering your threshold percentage (e.g., from 83% to 85%)
- Reduce minimum seller feedback temporarily
- Check that your keywords are matching relevant listings

### Spot Price Not Updating

- Check your internet connection
- Try alternative price sources in config.py
- Clear the price cache by restarting the app

### Scan Taking Too Long

- Reduce MAX_ITEMS_PER_SCAN in .env
- Increase API_CALL_DELAY_SECONDS in config.py
- Check eBay API status for outages

## 📝 Development Roadmap

### Completed ✅

- [x] Core scanning functionality
- [x] eBay API integration
- [x] Spot price fetching
- [x] ASW calculation for major coin types
- [x] Web dashboard
- [x] Database storage
- [x] Basic filtering

### Planned 🚧

- [ ] Advanced coin type recognition
- [ ] Machine learning for deal scoring
- [ ] Mobile-responsive design improvements
- [ ] SMS notifications
- [ ] Historical price charts
- [ ] Export deals to CSV
- [ ] Multi-marketplace support (other sites beyond eBay)
- [ ] Advanced seller analytics
- [ ] Deal alert mobile app

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is provided as-is for educational and personal use.

## ⚖️ Disclaimer

**Important**: This tool is for educational purposes only. The authors are not responsible for:
- Any financial losses from using this tool
- counterfeit or misrepresented items
- eBay account issues from API usage
- Missed deals or incorrect calculations

Always do your own research and verify listings before purchasing.

## 🙏 Acknowledgments

- eBay for providing the Browse API
- JM Bullion, SD Bullion, and APMEX for spot price data
- The silver stacking community for inspiration and feedback

---

**Happy Deal Hunting! 🥈💰**

Made with ❤️ by SuperNinja