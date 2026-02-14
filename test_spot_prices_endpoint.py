#!/usr/bin/env python3
"""
Test script for /api/spot_prices endpoint
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.multi_metal_spot_price import MultiMetalSpotPrice

print("=" * 60)
print("Testing /api/spot_prices Endpoint Logic")
print("=" * 60)

# Test the multi-metal spot price fetcher
spot_price = MultiMetalSpotPrice()

print("\n[Test 1] Fetching all spot prices...")
print("-" * 60)

all_prices = spot_price.get_all_spot_prices()

if all_prices:
    print("✓ Successfully fetched prices for all metals\n")
    
    for metal, price_data in all_prices.items():
        spot = price_data.get('spot_price')
        
        if spot:
            # Calculate threshold
            if metal == 'gold':
                threshold = spot * 0.85
                discount = "15%"
            elif metal == 'silver':
                threshold = spot * 0.83
                discount = "17%"
            else:
                threshold = spot * 0.90
                discount = "10%"
            
            print(f"{metal.upper()}:")
            print(f"  Spot Price: ${spot:,.2f}/oz")
            print(f"  Threshold:  ${threshold:,.2f}/oz ({discount} discount)")
            print(f"  Source:     {price_data.get('source')}")
            print(f"  Verified:   {price_data.get('verified')}")
            print()
        else:
            print(f"{metal.upper()}: ❌ Price not available")
            print()
else:
    print("❌ Failed to fetch prices")

print("=" * 60)
print("✅ Test complete!")
print("=" * 60)

# Show example API response format
print("\nExample API Response:")
print("-" * 60)
print("""
{
  "success": true,
  "data": {
    "silver": {
      "spot_price": 30.50,
      "threshold": 25.32,
      "source": "CoinGecko",
      "timestamp": "2026-02-05T19:30:00",
      "verified": true
    },
    "gold": {
      "spot_price": 4863.23,
      "threshold": 4133.75,
      "source": "CoinGecko",
      "timestamp": "2026-02-05T19:30:00",
      "verified": true
    },
    "platinum": { ... },
    "palladium": { ... }
  },
  "metals": ["silver", "gold", "platinum", "palladium"]
}
""")