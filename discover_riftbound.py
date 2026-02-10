import os
import requests
from dotenv import load_dotenv

def discover_riftbound():
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    headers = {"Authorization": f"Bearer {api_token}"}

    # 1. Find Expansion
    exp_url = "https://api.cardtrader.com/api/v2/expansions"
    response = requests.get(exp_url, headers=headers)
    expansions = response.json()
    
    riftbound_exp = [e for e in expansions if "Riftbound" in e['name']]
    
    if not riftbound_exp:
        print("Riftbound expansion not found.")
        # Print a few to see format
        print("First 5 expansions:", [e['name'] for e in expansions[:5]])
        return

    for exp in riftbound_exp:
        print(f"Found: {exp['name']} (ID: {exp['id']}, Game ID: {exp['game_id']})")
        
        # 2. Sample Blueprints to see rarity property
        bp_url = "https://api.cardtrader.com/api/v2/blueprints/export"
        params = {"expansion_id": exp['id']}
        bp_response = requests.get(bp_url, headers=headers, params=params)
        blueprints = bp_response.json()
        
        if blueprints:
            print(f"Total blueprints in {exp['name']}: {len(blueprints)}")
            # Sample properties of the first blueprint
            sample = blueprints[0]
            print(f"Sample Blueprint: {sample['name']}")
            print(f"Properties: {sample.get('properties_hash', {})}")
            
            # Collect all rarities found
            rarities = set()
            for bp in blueprints:
                props = bp.get('properties_hash', {})
                # Try common rarity keys
                rarity = props.get('rarity') or props.get('mtg_rarity') or props.get('rarity_short')
                if rarity:
                    rarities.add(rarity)
            
            if rarities:
                print(f"Rarities found: {rarities}")
            else:
                print("No rarity property found in properties_hash.")

if __name__ == "__main__":
    discover_riftbound()
