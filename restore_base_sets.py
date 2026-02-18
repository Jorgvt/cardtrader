import os
import csv
import requests
import re
from dotenv import load_dotenv

# Expansion IDs from earlier
EXPANSIONS = {
    "ogn": 4166, # Origins
    "ogs": 4275  # Origins Proving Grounds
}

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def restore_base_sets():
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # 1. Read existing cards to avoid duplicates
    existing_cards = {} # normalized_name -> row
    try:
        with open('cards.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_cards[normalize_name(row['Name'])] = row
    except Exception as e:
        print(f"Error reading cards.csv: {e}")
        return

    print(f"Initial cards in CSV: {len(existing_cards)}")

    # 2. Fetch from CardTrader for ogn and ogs
    for prefix, exp_id in EXPANSIONS.items():
        print(f"Fetching official blueprints for {prefix} (ID: {exp_id})...")
        url = "https://api.cardtrader.com/api/v2/blueprints/export"
        r = requests.get(url, headers=headers, params={"expansion_id": exp_id})
        blueprints = r.json()
        
        for bp in blueprints:
            props = bp.get('fixed_properties', {})
            coll_num = props.get('collector_number')
            if not coll_num: continue
            
            name = bp['name']
            norm_name = normalize_name(name)
            
            # If we already have a record for this card, skip it 
            # (preserves existing rich data from the original CSV if any)
            if norm_name in existing_cards:
                continue
                
            rarity = props.get('riftbound_rarity', 'Common')
            
            # Infer domain from collector number for ogn (001-240 approx)
            # Actually, better to just leave it as Unknown or try a simple map
            domain = "Unknown"
            try:
                n = int(re.sub(r'\D', '', coll_num))
                if 1 <= n <= 41: domain = "Fury"
                elif 42 <= n <= 82: domain = "Calm"
                elif 83 <= n <= 123: domain = "Mind"
                elif 124 <= n <= 164: domain = "Body"
                elif 165 <= n <= 205: domain = "Chaos"
                elif 206 <= n <= 246: domain = "Order"
            except:
                pass

            existing_cards[norm_name] = {
                "ID": f"{prefix}-{coll_num}",
                "Name": name,
                "Rarity": rarity,
                "Domain": domain,
                "Image URL": bp.get('image_url', '')
            }

    # 3. Write back everything
    header = ["ID", "Name", "V1", "V2", "V3", "V4", "V5", "Energy", "Might", "Power", "Card Type", "Rarity", "Domain", "Tags", "Ability", "Image URL"]
    
    with open('cards.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for name_norm in sorted(existing_cards.keys()):
            c = existing_cards[name_norm]
            # Construct row carefully to preserve empty columns
            row = [
                c.get("ID", ""),
                c.get("Name", ""),
                c.get("V1", ""), c.get("V2", ""), c.get("V3", ""), c.get("V4", ""), c.get("V5", ""),
                c.get("Energy", ""), c.get("Might", ""), c.get("Power", ""),
                c.get("Card Type", ""),
                c.get("Rarity", ""),
                c.get("Domain", ""),
                c.get("Tags", ""),
                c.get("Ability", ""),
                c.get("Image URL", "")
            ]
            writer.writerow(row)

    print(f"Final cards in CSV: {len(existing_cards)}")

if __name__ == "__main__":
    restore_base_sets()
