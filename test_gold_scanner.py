#!/usr/bin/env python3
"""
Test script for gold scanner integration
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.deal_scanner import DealScanner
from modules.multi_metal_spot_price import MultiMetalSpotPrice
from modules.gold_calculator import GoldCalculator
from config import Config

print("=" * 60)
print("Gold Scanner Integration Test")
print("=" * 60)

# Test 1: Gold Calculator
print("\n[Test 1] Gold Calculator Module")
print("-" * 60)
gold_calc = GoldCalculator()

test_titles = [
    "1 oz 24K Gold Bar .9999 Fine",
    "10 gram 22K Gold Coin",
    "1/4 oz 14K Gold Eagle",
    "Gold ring - 18K - 5 grams",
    "Invalid title without gold info"
]

for title in test_titles:
    # Create mock item details
    mock_item = {'title': title, 'price': 1000.0, 'shipping_cost': 0.0}
    result = gold_calc.calculate_agw(mock_item)
    if result['identified']:
        print(f"✓ Identified: {title}")
        print(f"  Weight: {result['agw']:.4f} oz | Purity: {result.get('purity', 'Unknown')}")
    else:
        print(f"✗ Not identified: {title}")

# Test 2: Multi-Metal Spot Price
print("\n[Test 2] Multi-Metal Spot Price Fetcher")
print("-" * 60)
spot_price = MultiMetalSpotPrice()

print("Fetching silver price...")
silver_info = spot_price.get_silver_price_info()
if silver_info['spot_price']:
    print(f"✓ Silver: ${silver_info['spot_price']:.2f}/oz (threshold: ${silver_info['threshold']:.2f})")
else:
    print("✗ Failed to fetch silver price")

print("\nFetching gold price...")
gold_info = spot_price.get_gold_price_info()
if gold_info['spot_price']:
    print(f"✓ Gold: ${gold_info['spot_price']:.2f}/oz (threshold: ${gold_info['threshold']:.2f})")
else:
    print("✗ Failed to fetch gold price")

# Test 3: Deal Scanner Initialization
print("\n[Test 3] Deal Scanner Initialization")
print("-" * 60)

try:
    silver_scanner = DealScanner(metal_type='silver')
    print("✓ Silver scanner initialized")
    
    gold_scanner = DealScanner(metal_type='gold')
    print("✓ Gold scanner initialized")
    print(f"  - Gold calculator loaded: {gold_scanner.gold_calculator is not None}")
    print(f"  - ASW calculator loaded: {gold_scanner.asw_calculator is not None}")
except Exception as e:
    print(f"✗ Failed to initialize scanner: {e}")

# Test 4: Deal Validation Methods
print("\n[Test 4] Deal Validation")
print("-" * 60)

# Mock gold deal data
mock_gold_deal = {
    'title': '1 oz 24K Gold Bar',
    'price': 4500.00,
    'shipping_cost': 0.00,
    'total_cost': 4500.00
}

mock_gold_info = {
    'identified': True,
    'agw': 1.0,
    'purity': 0.9999,
    'confidence': 0.95
}

if gold_info['spot_price']:
    mock_metrics = gold_calc.calculate_deal_metrics(mock_gold_deal, mock_gold_info, gold_info['spot_price'])
    print(f"✓ Deal metrics calculated:")
    print(f"  - Cost per oz: ${mock_metrics['cost_per_oz']:.2f}")
    print(f"  - Spot price: ${mock_metrics['spot_price']:.2f}")
    print(f"  - Discount: {mock_metrics['discount_percent']:.1f}%")
    print(f"  - Threshold: ${mock_metrics['threshold']:.2f}")
    
    is_valid = gold_calc.validate_deal(mock_gold_deal, mock_metrics)
    print(f"  - Valid deal: {'Yes' if is_valid else 'No'}")
else:
    print("✗ Skipped deal validation (no gold price)")

# Test 5: Configuration
print("\n[Test 5] Configuration")
print("-" * 60)
print(f"✓ Supported metals: {Config.SUPPORTED_METALS}")
print(f"✓ Silver keywords: {len(Config.SILVER_SEARCH_KEYWORDS)} keywords")
print(f"✓ Gold keywords: {len(Config.GOLD_SEARCH_KEYWORDS)} keywords")
print(f"✓ eBay coin category: {Config.EBAY_CATEGORY_COINS}")
print(f"✓ eBay bullion category: {Config.EBAY_CATEGORY_BULLION}")

print("\n" + "=" * 60)
print("✅ All integration tests completed!")
print("=" * 60)