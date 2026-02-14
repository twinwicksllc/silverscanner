#!/usr/bin/env python3
"""
Test gold price fetching with fallback sources
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.multi_metal_spot_price import MultiMetalSpotPrice

print("=" * 60)
print("Testing Gold Price Fetching with Fallback")
print("=" * 60)

spot_price = MultiMetalSpotPrice()

print("\n[Test 1] Fetching gold price with fallback...")
print("-" * 60)

gold_info = spot_price.get_gold_price_info()

if gold_info['spot_price']:
    print(f"✓ Gold Price: ${gold_info['spot_price']:,.2f}/oz")
    print(f"  Threshold:  ${gold_info['threshold']:,.2f}/oz (15% discount)")
    print(f"  Source:     {gold_info['source']}")
    print(f"  Verified:   {gold_info['verified']}")
    print(f"  Timestamp:  {gold_info['timestamp']}")
else:
    print("✗ Failed to fetch gold price from all sources")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)