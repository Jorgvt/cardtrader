import argparse
import os
import sys
import re
from app.games.fab import FABGame
from app.core import api

def main():
    parser = argparse.ArgumentParser(description="Generate a CardTrader-ready list of Flesh and Blood cards.")
    parser.add_argument("--class_name", required=True, help="Class name (e.g., Ninja, Warrior, Brute)")
    parser.add_argument("--rarity", required=True, help="Rarity (e.g., Common, Rare, Majestic)")
    parser.add_argument("--expansion", help="Expansion name (e.g., Rosetta, Uprising). If 'all', checks all expansions.")
    parser.add_argument("--quantity", type=int, default=1, help="Quantity for each card (default: 1)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--deduplicate", action="store_true", help="Only include the first occurrence of each card name across expansions.")

    args = parser.parse_args()

    game = FABGame()
    type_mapping = game.load_cards_mapping()
    all_identities = sorted(type_mapping.keys(), key=len, reverse=True)

    expansions_to_check = {}
    if not args.expansion or args.expansion.lower() == 'all':
        expansions_to_check = game.expansions
    else:
        # Match expansion exactly or by partial name
        for exp_name, exp_id in game.expansions.items():
            if args.expansion.lower() == exp_name.lower() or args.expansion.lower() in exp_name.lower():
                expansions_to_check[exp_name] = exp_id
        
        if not expansions_to_check:
            print(f"Error: Expansion '{args.expansion}' not found.")
            print("Available expansions:", ", ".join(game.expansions.keys()))
            sys.exit(1)

    # Dictionary to ensure deduplication
    final_list = {}
    exp_code_regex = re.compile(r'\s*\([^)]*[A-Z]{3,}[^)]*\)\s*')
    variant_regex = re.compile(r'\s*-\s*(unlimited|1st edition|rainbow foil|cold foil|foil).*', re.I)

    for exp_name, exp_id in expansions_to_check.items():
        print(f"Fetching blueprints for {exp_name}...", file=sys.stderr)
        try:
            blueprints = api.fetch_blueprints(exp_id)
            for bp in blueprints:
                # 1. Rarity Filter
                bp_rarity = bp.get('fixed_properties', {}).get('fab_rarity', '').lower()
                if bp_rarity != args.rarity.lower():
                    continue
                
                # 2. Identity Resolution
                bp_name = bp['name']
                norm_bp_name = game.normalize_name(bp_name)
                
                # Find the most specific identity that is a prefix of the blueprint name
                identity = None
                for ident in all_identities:
                    if norm_bp_name.startswith(ident):
                        identity = ident
                        break
                
                if not identity:
                    continue
                
                # 3. Class Filter
                card_types = type_mapping.get(identity, "")
                if args.class_name.lower() in card_types.lower():
                    # 4. Deduplication Logic
                    if args.deduplicate and identity in final_list:
                        continue

                    # Clean name for output
                    clean_name = exp_code_regex.sub(' ', bp_name)
                    clean_name = variant_regex.sub('', clean_name).strip()
                    
                    final_list[identity] = f"{args.quantity}x {clean_name}"
        except:
            continue

    if not final_list:
        print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Sort the items alphabetically by name
    sorted_items = sorted(final_list.values(), key=lambda x: x.split('x ', 1)[1])
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write("\n".join(sorted_items) + "\n")
        print(f"List saved to {args.output}", file=sys.stderr)
    else:
        print("\n".join(sorted_items))

if __name__ == "__main__":
    main()
