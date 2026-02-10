import os
import requests
import re
from dotenv import load_dotenv

def sanitize_filename(name):
    """Remove characters that are not allowed in filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def fetch_wishlist_contents():
    # Load environment variables from 'env' file
    load_dotenv(dotenv_path='env')
    
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        print("Error: API_CARDTRADER not found in env file.")
        return

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    # 1. Fetch all wishlists to get IDs and names
    list_url = "https://api.cardtrader.com/api/v2/wishlists"
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        wishlists = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching wishlist list: {e}")
        return

    # Create a directory for wishlist contents if it doesn't exist
    output_dir = "wishlists_content"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Fetch contents for each wishlist
    for wishlist in wishlists:
        w_id = wishlist['id']
        w_name = wishlist['name']
        
        print(f"Fetching contents for: {w_name} (ID: {w_id})...")
        
        detail_url = f"https://api.cardtrader.com/api/v2/wishlists/{w_id}"
        try:
            detail_response = requests.get(detail_url, headers=headers)
            detail_response.raise_for_status()
            wishlist_data = detail_response.json()
            
            items = wishlist_data.get('items', [])
            
            # Sanitize name for filename
            filename = f"{sanitize_filename(w_name)}_{w_id}.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                if not items:
                    f.write("(Empty wishlist)\n")
                for item in items:
                    qty = item.get('quantity', 1)
                    name = item.get('meta_name', 'Unknown Item')
                    # You can add more details like expansion_code, condition, etc.
                    f.write(f"{qty}x {name}\n")
            
            print(f"  -> Saved to {filepath}")

        except requests.exceptions.RequestException as e:
            print(f"  -> Error fetching details for {w_name}: {e}")

    print("\nAll wishlists processed.")

if __name__ == "__main__":
    fetch_wishlist_contents()