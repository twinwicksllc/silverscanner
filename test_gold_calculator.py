"""
Test script for GoldCalculator
"""

from modules.gold_calculator import GoldCalculator

def test_gold_calculator():
    calc = GoldCalculator()
    
    test_cases = [
        # Modern Bullion
        ("2024 1 oz American Gold Eagle BU", "Modern Bullion", 1.0),
        ("1/10 oz Gold Maple Leaf", "Modern Bullion", 0.1),
        ("South African Krugerrand 1 oz", "Modern Bullion", 1.0),
        
        # Pre-1933
        ("$20 Saint Gaudens Double Eagle MS63", "Pre-1933 US Gold", 0.9675),
        ("1907 $10 Indian Head Eagle", "Pre-1933 US Gold", 0.48375),
        ("$5 Liberty Half Eagle", "Pre-1933 US Gold", 0.24187),
        
        # Foreign
        ("British Gold Sovereign", "Foreign Gold Coin", 0.2354),
        
        # Bars
        ("10 gram PAMP Suisse Gold Bar", "Gold Bar", 0.3215),
        ("1 oz Gold Round", "Gold Round", 1.0),
        
        # Jewelry
        ("14k Gold Chain 15 grams", "14k Gold Jewelry", 0.2812),  # 15g * 0.03215 * 0.5833
        
        # Should reject
        ("Gold-plated coin", None, None),
        ("Gold tone necklace", None, None),
    ]
    
    print("=== Testing Gold Calculator ===\n")
    
    passed = 0
    failed = 0
    
    for title, expected_type, expected_agw in test_cases:
        result = calc.calculate_agw({'title': title})
        
        if expected_type is None:
            # Should be rejected
            if not result['identified']:
                print(f"✓ PASS: '{title}' correctly rejected")
                passed += 1
            else:
                print(f"✗ FAIL: '{title}' should be rejected but was identified as {result['coin_type']}")
                failed += 1
        else:
            # Should be identified
            if result['identified']:
                agw_match = abs(result['agw'] - expected_agw) < 0.01 if expected_agw else True
                type_match = expected_type in result['coin_type']
                
                if agw_match and type_match:
                    print(f"✓ PASS: '{title}'")
                    print(f"    Type: {result['coin_type']}, AGW: {result['agw']:.4f} oz, Purity: {result['purity']:.4f}")
                    passed += 1
                else:
                    print(f"✗ FAIL: '{title}'")
                    print(f"    Expected: {expected_type}, {expected_agw} oz")
                    print(f"    Got: {result['coin_type']}, {result['agw']:.4f} oz")
                    failed += 1
            else:
                print(f"✗ FAIL: '{title}' not identified")
                print(f"    Reason: {result.get('reason', 'unknown')}")
                failed += 1
        
        print()
    
    print(f"=== Results: {passed} passed, {failed} failed ===")
    return failed == 0

if __name__ == '__main__':
    success = test_gold_calculator()
    exit(0 if success else 1)
