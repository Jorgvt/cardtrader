import os
import csv
import requests
import re
from dotenv import load_dotenv

# Expansion IDs
EXPANSIONS = {
    "ogn": 4166, # Origins
    "ogs": 4275  # Origins Proving Grounds
}

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def sync_all():
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    headers = {"Authorization": f"Bearer {api_token}"}
    
    # 1. Fetch ALL blueprints for ALL expansions
    print("Fetching ALL blueprints from CardTrader...")
    all_blueprints = {} # (prefix, num) -> data
    
    for prefix, exp_id in EXPANSIONS.items():
        print(f"  -> {prefix} (ID: {exp_id})")
        r = requests.get("https://api.cardtrader.com/api/v2/blueprints/export", headers=headers, params={"expansion_id": exp_id})
        for bp in r.json():
            props = bp.get('fixed_properties', {})
            num = props.get('collector_number')
            if num:
                all_blueprints[(prefix, num)] = {
                    "name": bp['name'],
                    "rarity": props.get('riftbound_rarity', 'Common'),
                    "id": f"{prefix}-{num}"
                }
    
    # Spiritforged too
    print("  -> sfd (ID: 4299)")
    r = requests.get("https://api.cardtrader.com/api/v2/blueprints/export", headers=headers, params={"expansion_id": 4299})
    for bp in r.json():
        props = bp.get('fixed_properties', {})
        num = props.get('collector_number')
        if num:
            all_blueprints[("sfd", num)] = {
                "name": bp['name'],
                "rarity": props.get('riftbound_rarity', 'Common'),
                "id": f"sfd-{num}"
            }

    # 2. Read existing cards to preserve Domain if we have it
    print("Reading current cards.csv...")
    existing_data = {} # (prefix, num) -> {domain, ...}
    try:
        with open('cards.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prefix_num = row['ID'].split('-')
                if len(prefix_num) == 2:
                    existing_data[tuple(prefix_num)] = row
    except:
        pass

    # 3. Merging
    final_rows = []
    
    def get_domain(prefix, num):
        # Check existing first
        if (prefix, num) in existing_data:
            d = existing_data[(prefix, num)]['Domain'].strip('"').split(',')[0].strip()
            if d and d != "Unknown": return d
            
        # Heuristic for ogn/ogs if missing
        try:
            n = int(re.sub(r'\D', '', num))
            if prefix == "ogn":
                if 1 <= n <= 41: return "Fury"
                if 42 <= n <= 82: return "Calm"
                if 83 <= n <= 123: return "Mind"
                if 124 <= n <= 164: return "Body"
                if 165 <= n <= 205: return "Chaos"
                if 206 <= n <= 246: return "Order"
                # Legends/Epics often start at 247+
                # 247-248 (Fury/Mind), 249-250 (Fury/Body)...
                if n in [247, 248, 249, 250, 251, 252, 253, 254]: return "Fury"
                if n in [255, 256, 257, 258, 259, 260, 261, 262]: return "Calm"
                if n in [263, 264, 265, 266]: return "Mind"
                if n in [267, 268, 269, 270]: return "Body"
            if prefix == "sfd":
                if 1 <= n <= 30: return "Fury"
                if 31 <= n <= 60: return "Calm"
                if 61 <= n <= 90: return "Mind"
                if 91 <= n <= 120: return "Body"
                if 121 <= n <= 150: return "Chaos"
                if 151 <= n <= 180: return "Order"
        except:
            pass
        return "Unknown"

    header = ["ID", "Name", "V1", "V2", "V3", "V4", "V5", "Energy", "Might", "Power", "Card Type", "Rarity", "Domain", "Tags", "Ability", "Image URL"]
    
    for (prefix, num), bp in all_blueprints.items():
        domain = get_domain(prefix, num)
        
        # Preserve other stats if they exist
        existing = existing_data.get((prefix, num), {})
        
        row = [
            bp['id'],
            bp['name'],
            "", "", "", "", "", # V1-V5
            existing.get("Energy", ""),
            existing.get("Might", ""),
            existing.get("Power", ""),
            existing.get("Card Type", ""),
            bp['rarity'],
            domain,
            existing.get("Tags", ""),
            existing.get("Ability", ""),
            existing.get("Image URL", "")
        ]
        final_rows.append(row)

    # 4. Write CSV
    with open('cards.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(sorted(final_rows, key=lambda x: x[0]))

    print(f"Sync complete. Total cards: {len(final_rows)}")

if __name__ == "__main__":
    sync_all()
