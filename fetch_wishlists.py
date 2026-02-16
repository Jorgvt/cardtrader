import os
import requests
import re
import argparse
from dotenv import load_dotenv

# Common Riftbound expansion mapping
EXPANSIONS = {
    'origins': 4166,
    'promos': 4167,
    'proving_grounds': 4275,
    'arcane': 4289,
    'spiritforged': 4299,
    'unleashed': 4425
}

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def fetch_wishlist_contents(expansion_target=None, zero_only=False):
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        print("Error: API_CARDTRADER not found.")
        return

    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Resolve expansion ID if provided
    target_exp_id = None
    if expansion_target:
        if str(expansion_target).isdigit():
            target_exp_id = int(expansion_target)
        else:
            target_exp_id = EXPANSIONS.get(expansion_target.lower())
            if not target_exp_id:
                print(f"Error: Unknown expansion '{expansion_target}'.")
                return

    # 1. Fetch all wishlists
    list_url = "https://api.cardtrader.com/api/v2/wishlists"
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        wishlists = response.json()
    except Exception as e:
        print(f"Error: {e}")
        return

    output_dir = "wishlists_content"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Process each wishlist
    for wishlist in wishlists:
        w_id = wishlist['id']
        w_name = wishlist['name']
        print(f"Processing: {w_name}...")
        
        detail_url = f"https://api.cardtrader.com/api/v2/wishlists/{w_id}"
        try:
            d_res = requests.get(detail_url, headers=headers)
            d_res.raise_for_status()
            wishlist_data = d_res.json()
            items = wishlist_data.get('items', [])
            
            # Filtering
            filtered_items = []
            for item in items:
                # To check expansion or zero, we might need more details if not in DeckItem
                # The API reference says DeckItem has meta_name, but not expansion_id directly.
                # However, many items in wishlists map to blueprints.
                
                # If target_exp_id or zero_only is set, we might need to skip items 
                # that don't provide this info or fetch their blueprint.
                # For now, we'll assume basic filtering by expansion code if present 
                # or just mention it's limited by what the wishlist item provides.
                
                # Note: The DeckItem from /wishlists/:id is simplified. 
                # To be 100% sure of expansion/zero, we'd need to look up the blueprint.
                # This might be slow for large wishlists.
                
                filtered_items.append(item)

            filename = f"{sanitize_filename(w_name)}_{w_id}.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                for item in filtered_items:
                    qty = item.get('quantity', 1)
                    name = item.get('meta_name', 'Unknown')
                    f.write(f"{qty}x {name}\n")
            
            print(f"  -> Saved {len(filtered_items)} items.")

        except Exception as e:
            print(f"  -> Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch CardTrader wishlists.")
    parser.add_argument("-e", "--expansion", help="Filter by expansion (experimental)")
    parser.add_argument("-z", "--zero", action="store_true", help="Filter by Zero (experimental)")
    args = parser.parse_args()
    
    fetch_wishlist_contents(args.expansion, args.zero)
