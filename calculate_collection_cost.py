import os
import csv
import requests
import argparse
import re
import statistics
from dotenv import load_dotenv

# Map CSV ID prefixes to CardTrader expansion IDs
EXPANSION_MAP = {
    "ogn": 4166, # Origins
    "ogs": 4275, # Origins Proving Grounds
    "arc": 4289, # Arcane
    "sfd": 4299, # Spiritforged
    "unl": 4425, # Unleashed
}

# Reverse map for filtering by name/code
EXP_CODE_MAP = {
    "origins": "ogn",
    "proving_grounds": "ogs",
    "arcane": "arc",
    "spiritforged": "sfd",
    "unleashed": "unl"
}

def normalize_name(name):
    """Lowercases and removes all non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def calculate_cost(rarity_target, domain_target, quantity=1, zero_only=False, lang_target=None, expansion_filter=None, foil_target=False):
    # ... (rest of the function setup)
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        return {"error": "API_CARDTRADER not found"}

    headers = {"Authorization": f"Bearer {api_token}"}
    
    target_prefix = None
    if expansion_filter:
        target_prefix = EXP_CODE_MAP.get(expansion_filter.lower()) or expansion_filter.lower()

    cards_to_buy = []
    try:
        with open('cards.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Rarity'].lower() != rarity_target.lower(): continue
                if row['Domain'].lower() != domain_target.lower(): continue
                prefix = row['ID'].split('-')[0].lower()
                if target_prefix and prefix != target_prefix: continue
                cards_to_buy.append(row)
    except Exception as e:
        return {"error": f"Error reading csv: {str(e)}"}

    if not cards_to_buy:
        return {
            "count": 0,
            "total_cost": 0,
            "found_count": 0,
            "items_found": 0,
            "currency": "EUR"
        }

    total_cost_cents = 0
    found_count = 0
    total_items_found = 0
    currency = "EUR"
    blueprint_cache = {}

    for card in cards_to_buy:
        card_name = card['Name']
        card_name_norm = normalize_name(card_name)
        card_id = card['ID']
        prefix = card_id.split('-')[0].lower()
        exp_id = EXPANSION_MAP.get(prefix)

        if not exp_id: continue

        if exp_id not in blueprint_cache:
            bp_url = "https://api.cardtrader.com/api/v2/blueprints/export"
            try:
                bp_response = requests.get(bp_url, headers=headers, params={"expansion_id": exp_id})
                blueprint_cache[exp_id] = bp_response.json()
            except:
                continue

        collector_num = card_id.split('-', 1)[1] if '-' in card_id else None
        target_bp = None
        for bp in blueprint_cache.get(exp_id, []):
            if normalize_name(bp['name']) == card_name_norm:
                bp_coll_num = bp.get('fixed_properties', {}).get('collector_number')
                if collector_num and bp_coll_num:
                    if str(bp_coll_num).lower() == str(collector_num).lower():
                        target_bp = bp
                        break
                else:
                    target_bp = bp
                    break
        
        if not target_bp:
            for bp in blueprint_cache.get(exp_id, []):
                if normalize_name(bp['name']) == card_name_norm:
                    target_bp = bp
                    break

        if not target_bp: continue

        market_url = "https://api.cardtrader.com/api/v2/marketplace/products"
        try:
            m_response = requests.get(market_url, headers=headers, params={"blueprint_id": target_bp['id']})
            market_data = m_response.json()
            listings = market_data.get(str(target_bp['id']), [])
        except:
            continue

        # Filter by Zero compatibility if requested
        if zero_only:
            listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub') is True]

        # FILTER: Ignore graded and low condition
        listings = [
            l for l in listings 
            if not l.get('graded', False) 
            and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']
        ]

        if lang_target:
            listings = [l for l in listings if l.get('properties_hash', {}).get('riftbound_language', '').lower() == lang_target.lower()]

        if not listings: continue

        # FOIL LOGIC:
        # If foil_target is True, we only want foils.
        # If foil_target is False, we prioritize NON-foils, but take foils if that's all there is?
        # Actually, let's keep it simple: If foil_target is False, filter OUT foils unless explicitly requested.
        
        def is_foil(l):
            props = l.get('properties_hash', {})
            return props.get('riftbound_foil') or props.get('foil')

        if foil_target:
            listings = [l for l in listings if is_foil(l)]
        else:
            # Prioritize non-foils
            non_foils = [l for l in listings if not is_foil(l)]
            if non_foils:
                listings = non_foils
            # else: keep original (foils) if that's the only NM option

        if not listings: continue

        sorted_listings = sorted(listings, key=lambda x: x.get('price_cents', float('inf')))
        needed = quantity
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
        "total_cost": total_cost_cents / 100,
        "currency": currency
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cost for cards of a specific color and rarity.")
    parser.add_argument("rarity", help="Rarity (Epic, Rare, etc.)")
    parser.add_argument("domain", help="Domain (Fury, Calm, etc.)")
    parser.add_argument("language", nargs="?", help="Language (en, fr, etc.)")
    parser.add_argument("-q", "--quantity", type=int, default=1, help="Quantity each (default: 1)")
    parser.add_argument("-z", "--zero", action="store_true", help="Zero compatibility only")
    parser.add_argument("-e", "--expansion", help="Filter by expansion name/code (origins, proving_grounds, etc.)")
    parser.add_argument("-f", "--foil", action="store_true", help="Only include foil listings")
    
    args = parser.parse_args()
    result = calculate_cost(args.rarity, args.domain, args.quantity, args.zero, args.language, args.expansion, args.foil)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n--- Results ---")
        print(f"Target: {result['count']} cards, {args.quantity} copies (Total: {result['count']*args.quantity})")
        print(f"Items found: {result['items_found']}/{result['count']*args.quantity}")
        print(f"Total Cost: {result['total_cost']:.2f} {result['currency']}")


