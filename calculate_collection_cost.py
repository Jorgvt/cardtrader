import os
import csv
import requests
import argparse
import re
from dotenv import load_dotenv

# Map CSV Set names to CardTrader expansion IDs
EXPANSION_MAP = {
    "origins": 4166,
    "proving grounds": 4275,
    "sfd": 4299,
    "spiritforged": 4299,
    "arcane": 4289,
    "unleashed": 4425
}

def normalize_name(name):
    """Lowercases and removes all non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def load_inventory(inventory_file):
    """Loads user collection from a CSV file."""
    inventory = {} # normalized_name -> quantity
    if not inventory_file or not os.path.exists(inventory_file):
        return inventory
    
    try:
        with open(inventory_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('Name')
                qty = row.get('Quantity', 0)
                if name:
                    inventory[normalize_name(name)] = int(qty)
    except Exception as e:
        print(f"Warning: Error loading inventory {inventory_file}: {e}")
    
    return inventory

def calculate_cost(rarity_target, domain_target, quantity=1, zero_only=False, lang_target=None, expansion_filter=None, foil_target=False, inventory=None):
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        return {"error": "API_CARDTRADER not found"}

    headers = {"Authorization": f"Bearer {api_token}"}
    
    # 1. Parse New CSV and filter cards
    cards_to_buy = []
    try:
        with open('riftbound_cards_by_set.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Basic filters
                if row['Rarity'].lower() != rarity_target.lower(): continue
                
                # Dominion check (handles "Fury, Body" etc)
                card_domains = [d.strip().lower() for d in row['Dominion'].split(',')]
                if domain_target.lower() not in card_domains: continue
                
                # Expansion filter
                if expansion_filter and row['Set'].lower() != expansion_filter.lower(): continue
                
                # Calculate needed quantity based on inventory
                target_qty = quantity
                if inventory:
                    owned_qty = inventory.get(normalize_name(row['Name']), 0)
                    target_qty = max(0, quantity - owned_qty)
                
                if target_qty > 0:
                    row['_needed_qty'] = target_qty
                    cards_to_buy.append(row)
                    
    except Exception as e:
        return {"error": f"Error reading riftbound_cards_by_set.csv: {str(e)}"}

    if not cards_to_buy:
        return {
            "rarity": rarity_target,
            "domain": domain_target,
            "count": 0,
            "total_cost": 0,
            "found_count": 0,
            "items_found": 0,
            "currency": "EUR",
            "using_inventory": bool(inventory)
        }

    total_cost_cents = 0
    found_count = 0
    total_items_found = 0
    total_items_needed = sum(c['_needed_qty'] for c in cards_to_buy)
    currency = "EUR"
    blueprint_cache = {}

    for card in cards_to_buy:
        card_name = card['Name']
        card_name_norm = normalize_name(card_name)
        set_name = card['Set'].lower()
        exp_id = EXPANSION_MAP.get(set_name)

        if not exp_id:
            if expansion_filter and expansion_filter.isdigit():
                exp_id = int(expansion_filter)
            else:
                continue

        if exp_id not in blueprint_cache:
            bp_url = "https://api.cardtrader.com/api/v2/blueprints/export"
            try:
                bp_response = requests.get(bp_url, headers=headers, params={"expansion_id": exp_id})
                blueprint_cache[exp_id] = bp_response.json()
            except:
                continue

        target_bp = None
        for bp in blueprint_cache.get(exp_id, []):
            if normalize_name(bp['name']) == card_name_norm:
                if bp.get('version') in [None, '']:
                    target_bp = bp
                    break
                target_bp = bp
        
        if not target_bp: continue

        market_url = "https://api.cardtrader.com/api/v2/marketplace/products"
        try:
            m_response = requests.get(market_url, headers=headers, params={"blueprint_id": target_bp['id']})
            market_data = m_response.json()
            listings = market_data.get(str(target_bp['id']), [])
        except:
            continue

        if zero_only:
            listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub') is True]

        listings = [
            l for l in listings 
            if not l.get('graded', False) 
            and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']
        ]

        if lang_target:
            listings = [l for l in listings if l.get('properties_hash', {}).get('riftbound_language', '').lower() == lang_target.lower()]

        def is_foil(l):
            props = l.get('properties_hash', {})
            return props.get('riftbound_foil') or props.get('foil')

        if foil_target:
            listings = [l for l in listings if is_foil(l)]
        else:
            non_foils = [l for l in listings if not is_foil(l)]
            if non_foils: listings = non_foils

        if not listings: continue

        sorted_listings = sorted(listings, key=lambda x: x.get('price_cents', float('inf')))
        needed = card['_needed_qty']
        card_total_cents = 0
        card_items_found = 0
        
        for l in sorted_listings:
            price = l.get('price_cents')
            if price is None: continue
            avail = l.get('quantity', 1)
            to_take = min(avail, needed)
            card_total_cents += to_take * price
            needed -= to_take
            card_items_found += to_take
            currency = l.get('price_currency', currency)
            if needed <= 0: break
        
        if card_items_found > 0:
            total_cost_cents += card_total_cents
            total_items_found += card_items_found
            found_count += 1

    return {
        "rarity": rarity_target,
        "domain": domain_target,
        "count": len(cards_to_buy),
        "found_count": found_count,
        "items_found": total_items_found,
        "items_needed": total_items_needed,
        "total_cost": total_cost_cents / 100,
        "currency": currency,
        "using_inventory": bool(inventory)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cost for cards using riftbound_cards_by_set.csv")
    parser.add_argument("rarity", help="Rarity (Epic, Rare, etc.)")
    parser.add_argument("domain", help="Domain (Fury, Calm, etc.)")
    parser.add_argument("language", nargs="?", help="Language (en, fr, etc.)")
    parser.add_argument("-q", "--quantity", type=int, default=1, help="Quantity each (default: 1)")
    parser.add_argument("-z", "--zero", action="store_true", help="Zero compatibility only")
    parser.add_argument("-e", "--expansion", help="Filter by expansion name (Origins, SFD, etc.)")
    parser.add_argument("-f", "--foil", action="store_true", help="Only include foil listings")
    parser.add_argument("-i", "--inventory", help="Path to collection.csv file")
    
    args = parser.parse_args()
    
    inventory = load_inventory(args.inventory)
    result = calculate_cost(args.rarity, args.domain, args.quantity, args.zero, args.language, args.expansion, args.foil, inventory)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n--- Results (Using riftbound_cards_by_set.csv) ---")
        if result['using_inventory']:
            print("Filtering by owned cards in inventory.")
        print(f"Target: {result['count']} unique cards missing, {result['items_needed']} total items needed")
        print(f"Items found: {result['items_found']}/{result['items_needed']}")
        print(f"Total Cost: {result['total_cost']:.2f} {result['currency']}")
