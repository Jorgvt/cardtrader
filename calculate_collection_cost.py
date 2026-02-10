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
}

def normalize_name(name):
    """Lowercases and removes all non-alphanumeric characters."""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def calculate_cost(rarity_target, domain_target, quantity=1, zero_only=False, lang_target=None):
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        print("Error: API_CARDTRADER not found.")
        return

    headers = {"Authorization": f"Bearer {api_token}"}
    
    # 1. Parse CSV and filter cards
    cards_to_buy = []
    try:
        with open('cards.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Rarity'].lower() == rarity_target.lower() and row['Domain'].lower() == domain_target.lower():
                    cards_to_buy.append(row)
    except Exception as e:
        print(f"Error reading cards.csv: {e}")
        return

    if not cards_to_buy:
        print(f"No cards found for rarity '{rarity_target}' and domain '{domain_target}'.")
        return

    zero_str = " (Zero Only)" if zero_only else ""
    qty_str = f" x{quantity} each" if quantity > 1 else ""
    lang_str = f" in language '{lang_target}'" if lang_target else ""
    print(f"Found {len(cards_to_buy)} cards. Fetching prices{zero_str}{qty_str}{lang_str} from CardTrader...")

    total_cost_cents = 0
    missing_cards = []
    partially_filled = []
    found_count = 0
    total_items_found = 0
    currency = "EUR"

    blueprint_cache = {}

    for card in cards_to_buy:
        card_name = card['Name']
        card_name_norm = normalize_name(card_name)
        card_id = card['ID']
        prefix = card_id.split('-')[0]
        exp_id = EXPANSION_MAP.get(prefix)

        if not exp_id:
            missing_cards.append(f"{card_name} (Unknown expansion)")
            continue

        if exp_id not in blueprint_cache:
            bp_url = "https://api.cardtrader.com/api/v2/blueprints/export"
            bp_response = requests.get(bp_url, headers=headers, params={"expansion_id": exp_id})
            blueprint_cache[exp_id] = bp_response.json()

        collector_num = card_id.split('-', 1)[1] if '-' in card_id else None
        
        target_bp = None
        for bp in blueprint_cache[exp_id]:
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
            # Final fallback
            for bp in blueprint_cache[exp_id]:
                if normalize_name(bp['name']) == card_name_norm:
                    target_bp = bp
                    break

        if not target_bp:
            missing_cards.append(card_name)
            continue

        market_url = "https://api.cardtrader.com/api/v2/marketplace/products"
        m_response = requests.get(market_url, headers=headers, params={"blueprint_id": target_bp['id']})
        market_data = m_response.json()
        listings = market_data.get(str(target_bp['id']), [])

        # Filter by Zero compatibility if requested
        if zero_only:
            listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub') is True]

        # Filter by Language if requested
        if lang_target:
            listings = [
                l for l in listings 
                if l.get('properties_hash', {}).get('riftbound_language', '').lower() == lang_target.lower()
            ]

        if not listings:
            missing_cards.append(card_name)
            continue

        # Sort by price ascending
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
            
            if needed <= 0:
                break
        
        if card_items_found > 0:
            total_cost_cents += card_total_cents
            total_items_found += card_items_found
            found_count += 1
            if needed > 0:
                partially_filled.append(f"{card_name} (found {card_items_found}/{quantity})")
        else:
            missing_cards.append(card_name)


    print("\n--- Results ---")
    print(f"Target: {len(cards_to_buy)} unique cards, {quantity} copies each (Total: {len(cards_to_buy)*quantity})")
    print(f"Unique cards found: {found_count}/{len(cards_to_buy)}")
    print(f"Total items found: {total_items_found}/{len(cards_to_buy)*quantity}")
    print(f"Total Cost: {total_cost_cents/100:.2f} {currency}")
    
    if partially_filled:
        print(f"\nPartially Filled ({len(partially_filled)}):")
        for p in partially_filled[:5]:
            print(f"  - {p}")
    
    if missing_cards:
        print(f"\nMissing Entirely ({len(missing_cards)}):")
        for m in missing_cards[:10]:
            print(f"  - {m}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate cost to buy all cards of a specific color and rarity.")
    parser.add_argument("rarity", help="Rarity level (e.g., Common, Uncommon, Rare, Epic)")
    parser.add_argument("domain", help="Domain/Color (e.g., Fury, Calm, Mind, Body, Chaos, Order)")
    parser.add_argument("language", nargs="?", help="Language code (e.g., en, fr)")
    parser.add_argument("-q", "--quantity", type=int, default=1, help="Desired quantity of each card (default: 1)")
    parser.add_argument("-z", "--zero", action="store_true", help="Only include CardTrader Zero compatible listings")
    parser.add_argument("-l", "--language-flag", dest="lang_flag", help="Language code (flag version)")
    
    args = parser.parse_args()
    
    final_lang = args.lang_flag or args.language
    calculate_cost(args.rarity, args.domain, args.quantity, args.zero, final_lang)