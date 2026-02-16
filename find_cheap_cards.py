import os
import requests
import statistics
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

def find_cheap_cards(rarity_target, lang_target=None, expansion_target=4166, zero_only=False):
    load_dotenv(dotenv_path='env')
    api_token = os.getenv('API_CARDTRADER')
    if not api_token:
        print("Error: API_CARDTRADER not found.")
        return

    headers = {"Authorization": f"Bearer {api_token}"}
    
    # Resolve expansion ID
    exp_id = expansion_target
    if isinstance(expansion_target, str):
        if expansion_target.isdigit():
            exp_id = int(expansion_target)
        else:
            exp_id = EXPANSIONS.get(expansion_target.lower())
            if not exp_id:
                print(f"Error: Unknown expansion name '{expansion_target}'.")
                print(f"Known names: {', '.join(EXPANSIONS.keys())}")
                return

    # 1. Fetch Blueprints for the expansion
    print(f"Fetching blueprints for expansion ID {exp_id}...")
    bp_url = "https://api.cardtrader.com/api/v2/blueprints/export"
    params = {"expansion_id": exp_id}
    try:
        response = requests.get(bp_url, headers=headers, params=params)
        response.raise_for_status()
        all_blueprints = response.json()
    except Exception as e:
        print(f"Error fetching blueprints: {e}")
        return

    # 2. Filter by Rarity
    target_blueprints = [
        bp for bp in all_blueprints 
        if bp.get('fixed_properties', {}).get('riftbound_rarity', '').lower() == rarity_target.lower()
    ]

    if not target_blueprints:
        print(f"No cards found with rarity: {rarity_target}")
        return

    lang_str = f" in language '{lang_target}'" if lang_target else ""
    zero_str = " (Zero Only)" if zero_only else ""
    print(f"Found {len(target_blueprints)} cards with rarity '{rarity_target}'{lang_str}{zero_str}. Checking prices...")

    # 3. Check Marketplace Listings for each blueprint
    for bp in target_blueprints:
        bp_id = bp['id']
        bp_name = bp['name']
        
        market_url = "https://api.cardtrader.com/api/v2/marketplace/products"
        market_params = {"blueprint_id": bp_id}
        
        try:
            m_response = requests.get(market_url, headers=headers, params=market_params)
            m_response.raise_for_status()
            data = m_response.json()
            
            listings = data.get(str(bp_id), [])
            
            if not listings:
                continue

            if zero_only:
                listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub') is True]

            if lang_target:
                listings = [
                    l for l in listings 
                    if l.get('properties_hash', {}).get('riftbound_language', '').lower() == lang_target.lower()
                ]

            if not listings:
                continue

            prices = sorted([l['price_cents'] for l in listings if 'price_cents' in l])
            
            if len(prices) < 4:
                continue 

            cheapest = prices[0]
            comparison_pool = prices[1:6] 
            floor_avg = statistics.mean(comparison_pool)
            
            if cheapest <= floor_avg * 0.80:
                currency = listings[0].get('price_currency', '???')
                print(f"\n[CHEAP FIND] {bp_name} ({lang_target if lang_target else 'Any Lang'})")
                print(f"  Cheapest: {cheapest/100:.2f} {currency}")
                print(f"  Floor Avg (Next {len(comparison_pool)}): {floor_avg/100:.2f} {currency}")
                print(f"  Discount vs Floor: {((1 - cheapest/floor_avg)*100):.1f}%")
                print(f"  Link: https://www.cardtrader.com/cards/{bp_id}")

        except Exception as e:
            print(f"  Error checking {bp_name}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find cheap Riftbound cards on CardTrader.")
    parser.add_argument("rarity", nargs="?", help="Rarity level (e.g., Epic, Rare)")
    parser.add_argument("language", nargs="?", help="Language code (e.g., en, fr)")
    parser.add_argument("-e", "--expansion", default="origins", help="Expansion name or ID (default: origins)")
    parser.add_argument("-z", "--zero", action="store_true", help="Only CardTrader Zero compatible listings")

    args = parser.parse_args()

    if not args.rarity:
        parser.print_help()
    else:
        find_cheap_cards(args.rarity, args.language, args.expansion, args.zero)
