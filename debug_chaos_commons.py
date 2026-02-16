import os
import csv
import requests
import re
from dotenv import load_dotenv

# Re-using logic from main script
EXPANSION_MAP = {"ogn": 4166, "ogs": 4275, "arc": 4289, "sfd": 4299, "unl": 4425}

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def debug_category(rarity_target, domain_target):
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    headers = {"Authorization": f"Bearer {api_token}"}
    
    print(f"--- Debugging {rarity_target} {domain_target} ---")
    
    # 1. Get cards from CSV
    cards = []
    with open('cards.csv', mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Rarity'].lower() == rarity_target.lower() and row['Domain'].lower() == domain_target.lower():
                cards.append(row)
    
    print(f"Found {len(cards)} cards in CSV.\n")

    blueprint_cache = {}

    for card in cards:
        name = card['Name']
        c_id = card['ID']
        prefix = c_id.split('-')[0].lower()
        exp_id = EXPANSION_MAP.get(prefix)
        
        if not exp_id: continue
        if exp_id not in blueprint_cache:
            r = requests.get("https://api.cardtrader.com/api/v2/blueprints/export", headers=headers, params={"expansion_id": exp_id})
            blueprint_cache[exp_id] = r.json()

        # Find BP
        norm_name = normalize_name(name)
        target_bp = next((b for b in blueprint_cache[exp_id] if normalize_name(b['name']) == norm_name), None)
        
        if not target_bp:
            print(f"MISSING BP: {name}")
            continue

        # Get Listings
        m_res = requests.get(f"https://api.cardtrader.com/api/v2/marketplace/products", headers=headers, params={"blueprint_id": target_bp['id']})
        listings = m_res.json().get(str(target_bp['id']), [])
        
        # Apply current filters
        filtered = [
            l for l in listings 
            if not l.get('graded', False) 
            and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']
        ]
        
        if not filtered:
            print(f"NO NM LISTINGS: {name} (ID: {target_bp['id']})")
            continue

        # Sort and pick cheapest
        sorted_l = sorted(filtered, key=lambda x: x.get('price_cents', 999999))
        cheapest = sorted_l[0]
        
        print(f"CARD: {name}")
        print(f"  Cheapest NM: {cheapest['price_cents']/100:.2f} {cheapest['price_currency']}")
        print(f"  Seller: {cheapest.get('user', {}).get('name')} (Zero: {cheapest.get('user', {}).get('can_sell_via_hub')})")
        print(f"  Condition: {cheapest.get('properties_hash', {}).get('condition')}")
        # Check for foil
        is_foil = cheapest.get('properties_hash', {}).get('riftbound_foil') or cheapest.get('properties_hash', {}).get('foil')
        print(f"  Foil: {is_foil}")
        print("-" * 30)

if __name__ == "__main__":
    debug_category("Common", "Chaos")
