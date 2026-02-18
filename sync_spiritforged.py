import os
import csv
import requests
import re
from dotenv import load_dotenv

# Map CSV ID prefixes to CardTrader expansion IDs
EXP_ID = 4299 # Spiritforged

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def get_domain_from_number(num):
    try:
        n = int(re.sub(r'\D', '', str(num)))
        if 1 <= n <= 30: return "Fury"
        if 31 <= n <= 60: return "Calm"
        if 61 <= n <= 90: return "Mind"
        if 91 <= n <= 120: return "Body"
        if 121 <= n <= 150: return "Chaos"
        if 151 <= n <= 180: return "Order"
        # 181-221 are usually more complex or mixed, but let's try to map them if possible
        # Or look at them manually.
        return "Unknown"
    except:
        return "Unknown"

def sync_spiritforged():
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    headers = {"Authorization": f"Bearer {api_token}"}
    
    print("Fetching official Spiritforged blueprints...")
    url = "https://api.cardtrader.com/api/v2/blueprints/export"
    r = requests.get(url, headers=headers, params={"expansion_id": EXP_ID})
    blueprints = r.json()

    # Parse raw checklist for domains
    print("Reading domains from checklist...")
    checklist_domains = {} # name -> domain
    current_domain = "Unknown"
    valid_domains = ["Fury", "Calm", "Mind", "Body", "Chaos", "Order", "Colorless", "Battlefield", "Legend"]
    
    try:
        with open('spiritforged_raw.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 15: continue
                dom_check = row[11].strip()
                if dom_check in valid_domains:
                    current_domain = dom_check
                
                name_cell = row[14].strip()
                if name_cell:
                    checklist_domains[normalize_name(name_cell)] = current_domain
    except FileNotFoundError:
        print("spiritforged_raw.csv not found.")

    new_cards = []
    for bp in blueprints:
        props = bp.get('fixed_properties', {})
        coll_num = props.get('collector_number')
        if not coll_num: continue
        
        name = bp['name']
        norm_name = normalize_name(name)
        rarity = props.get('riftbound_rarity', 'Common')
        
        # 1. Try domain from checklist
        domain = checklist_domains.get(norm_name)
        
        # 2. Fallback to number range
        if not domain or domain == "Unknown" or domain == "Legend":
            domain = get_domain_from_number(coll_num)
            
        # 3. If it's a Legend, often it has mixed domains in Origins, 
        # but for the grid we need ONE.
        if domain == "Legend":
            # Heuristic: Legends in 181-221 often follow the same order?
            domain = get_domain_from_number(coll_num)

        new_cards.append({
            "ID": f"sfd-{coll_num}",
            "Name": name,
            "Rarity": rarity,
            "Domain": domain
        })

    # Clean existing sfd entries from cards.csv
    print("Cleaning and updating cards.csv...")
    header = ["ID", "Name", "V1", "V2", "V3", "V4", "V5", "Energy", "Might", "Power", "Card Type", "Rarity", "Domain", "Tags", "Ability", "Image URL"]
    final_rows = []
    
    try:
        with open('cards.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] != "ID" and not row[0].startswith("sfd-"):
                    final_rows.append(row)
    except FileNotFoundError:
        pass

    # Add new sfd cards
    added_ids = set()
    for c in new_cards:
        if c['ID'] not in added_ids:
            # Create a full row
            row = [c['ID'], c['Name'], "", "", "", "", "", "", "", "", "", c['Rarity'], c['Domain'], "", "", ""]
            final_rows.append(row)
            added_ids.add(c['ID'])

    with open('cards.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(final_rows)

    print(f"Done. Updated {len(added_ids)} Spiritforged cards.")

if __name__ == "__main__":
    sync_spiritforged()