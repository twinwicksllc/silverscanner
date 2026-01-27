#!/usr/bin/env python3
"""Check live Render application status and trigger scan"""

import requests
import json

def check_render():
    render_url = 'https://scanner.teckstart.com'
    
    print('=' * 70)
    print('LIVE RENDER APPLICATION CHECK')
    print('=' * 70)
    
    # 1. Check health
    print('\n1. Checking Health Status:')
    print('-' * 70)
    try:
        response = requests.get(f'{render_url}/healthz', timeout=10)
        print(f'   Status Code: {response.status_code}')
        print(f'   Response: {response.json()}')
    except Exception as e:
        print(f'   Error: {e}')
    
    # 2. Get current spot price
    print('\n2. Getting Current Spot Price:')
    print('-' * 70)
    try:
        response = requests.get(f'{render_url}/api/price', timeout=30)
        print(f'   Status Code: {response.status_code}')
        data = response.json()
        print(f'   Price: ${data.get("price", "N/A")}/oz')
        print(f'   Source: {data.get("source", "N/A")}')
        print(f'   Threshold: ${data.get("threshold", "N/A")}/oz')
    except Exception as e:
        print(f'   Error: {e}')
    
    # 3. Trigger a scan
    print('\n3. Triggering Scan:')
    print('-' * 70)
    try:
        response = requests.post(f'{render_url}/api/scan', timeout=120)
        print(f'   Status Code: {response.status_code}')
        data = response.json()
        print(f'   Status: {data.get("status", "N/A")}')
        print(f'   Message: {data.get("message", "N/A")}')
        print(f'   Items scanned: {data.get("items_scanned", 0)}')
        print(f'   Deals found: {data.get("deals_found", 0)}')
    except Exception as e:
        print(f'   Error: {e}')
    
    # 4. Get price history
    print('\n4. Getting Price History:')
    print('-' * 70)
    try:
        response = requests.get(f'{render_url}/api/price/history?days=1', timeout=10)
        print(f'   Status Code: {response.status_code}')
        data = response.json()
        history = data.get('history', [])
        print(f'   Entries: {len(history)}')
        if history:
            latest = history[-1]
            print(f'   Latest price: ${latest.get("price", "N/A")}/oz')
            print(f'   Latest source: {latest.get("source", "N/A")}')
            print(f'   Latest timestamp: {latest.get("timestamp", "N/A")}')
    except Exception as e:
        print(f'   Error: {e}')
    
    # 5. Get deals
    print('\n5. Getting Recent Deals:')
    print('-' * 70)
    try:
        response = requests.get(f'{render_url}/api/deals', timeout=10)
        print(f'   Status Code: {response.status_code}')
        data = response.json()
        deals = data.get('deals', [])
        print(f'   Total deals: {len(deals)}')
        if deals:
            latest_deal = deals[0]
            print(f'   Latest deal:')
            print(f'      Title: {latest_deal.get("title", "N/A")}')
            print(f'      Price: ${latest_deal.get("total_cost", 0):.2f}')
            print(f'      Discount: {latest_deal.get("discount_percent", 0):.1f}%')
    except Exception as e:
        print(f'   Error: {e}')
    
    print('\n' + '=' * 70)

if __name__ == '__main__':
    check_render()