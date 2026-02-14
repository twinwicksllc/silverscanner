#!/usr/bin/env python3
"""Test script to verify silver price fallback works"""
import sys
sys.path.insert(0, '/workspace/silverscanner')

from modules.multi_metal_spot_price import MultiMetalSpotPrice

print("Testing silver price with fallback...")
print("-" * 60)

multi_spot = MultiMetalSpotPrice()

# Test silver price info
silver_info = multi_spot.get_silver_price_info()

print(f"Silver Price Info:")
print(f"  Spot Price: ${silver_info.get('spot_price'):.2f}/oz" if silver_info.get('spot_price') else "  Spot Price: None")
print(f"  Threshold: ${silver_info.get('threshold'):.2f}/oz" if silver_info.get('threshold') else "  Threshold: None")
print(f"  Source: {silver_info.get('source')}")
print(f"  Verified: {silver_info.get('verified')}")
print(f"  Timestamp: {silver_info.get('timestamp')}")
print("-" * 60)

# Test gold price for comparison
gold_info = multi_spot.get_gold_price_info()
print(f"\nGold Price Info (for comparison):")
print(f"  Spot Price: ${gold_info.get('spot_price'):.2f}/oz" if gold_info.get('spot_price') else "  Spot Price: None")
print(f"  Threshold: ${gold_info.get('threshold'):.2f}/oz" if gold_info.get('threshold') else "  Threshold: None")
print(f"  Source: {gold_info.get('source')}")