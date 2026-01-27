import requests
import os
from dotenv import load_dotenv

# Load your new keys from the .env file
load_dotenv()

def test_ebay_connection():
    # Credentials from your .env
    client_id = os.getenv('EBAY_CLIENT_ID')
    client_secret = os.getenv('EBAY_CLIENT_SECRET')
    
    if not client_id or client_id == "your-sandbox-client-id-here":
        print("❌ Error: Please add your actual sandbox credentials to .env file")
        print("   EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set")
        return
    
    # Step 1: Get OAuth token using Client Credentials flow
    auth_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    
    auth_data = {
        'grant_type': 'client_credentials',
        'scope': 'https://api.ebay.com/oauth/api_scope'
    }
    
    print(f"--- Step 1: Getting OAuth Token ---")
    print(f"Client ID: {client_id[:10]}... (masked)")
    
    try:
        auth_response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data=auth_data
        )
        
        if auth_response.status_code != 200:
            print(f"❌ Authentication Failed!")
            print(f"   Status Code: {auth_response.status_code}")
            print(f"   Error: {auth_response.text}")
            return
        
        token_data = auth_response.json()
        access_token = token_data['access_token']
        print(f"✅ OAuth Token obtained successfully!")
        
        # Step 2: Search for items using the token
        search_url = "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY-US"
        }
        
        params = {
            "q": "silver coin",
            "limit": 3,
            "filter": "buyingOptions:{FIXED_PRICE}"
        }
        
        print(f"\n--- Step 2: Searching for Items ---")
        search_response = requests.get(search_url, headers=headers, params=params)
        
        if search_response.status_code == 200:
            data = search_response.json()
            items = data.get('itemSummaries', [])
            
            if items:
                print(f"✅ Success! Found {len(items)} items in Sandbox:")
                for i, item in enumerate(items, 1):
                    title = item.get('title', 'N/A')
                    price = item.get('price', {}).get('value', 'N/A')
                    currency = item.get('price', {}).get('currency', 'USD')
                    print(f"   {i}. {title}")
                    print(f"      Price: {currency} {price}")
            else:
                print(f"✅ Connection successful but no items found (Sandbox may be empty)")
        else:
            print(f"❌ Search Failed!")
            print(f"   Status Code: {search_response.status_code}")
            print(f"   Error: {search_response.text}")
    
    except Exception as e:
        print(f"⚠️ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 eBay Sandbox Connection Test")
    print("=" * 50)
    test_ebay_connection()
    print("=" * 50)