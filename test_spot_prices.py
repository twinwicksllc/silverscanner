"""
Test multi-metal spot price fetching
"""

from modules.multi_metal_spot_price import MultiMetalSpotPrice

def test_spot_prices():
    fetcher = MultiMetalSpotPrice()
    
    print("=== Testing Multi-Metal Spot Price Fetcher ===\n")
    
    metals = ['gold', 'silver', 'platinum', 'palladium']
    
    for metal in metals:
        print(f"Fetching {metal.title()} spot price...")
        try:
            result = fetcher.get_spot_price(metal)
            
            if result['spot_price']:
                print(f"✓ {metal.title()}: ${result['spot_price']:.2f}/oz")
                print(f"  Source: {result['source']}")
                print(f"  Verified: {result['verified']}")
            else:
                print(f"✗ {metal.title()}: Failed to fetch")
                print(f"  Source: {result['source']}")
        except Exception as e:
            print(f"✗ {metal.title()}: Error - {e}")
        
        print()

if __name__ == '__main__':
    test_spot_prices()
