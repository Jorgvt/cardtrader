import time
import argparse
from calculate_collection_cost import calculate_cost
from database import save_price, init_db

# Standard Riftbound values
RARITIES = ["Common", "Uncommon", "Rare", "Epic"]
DOMAINS = ["Fury", "Calm", "Mind", "Body", "Chaos", "Order"]

def run_update(quantities, zero_only, languages):
    """
    Iterates through combinations and updates the database.
    """
    init_db()
    total_updates = 0
    
    print(f"Starting automated update for:")
    print(f"  Quantities: {quantities}")
    print(f"  Zero Only:  {zero_only}")
    print(f"  Languages:  {languages}")
    
    for q in quantities:
        for z in zero_only:
            for lang in languages:
                # Handle "None" or "any" as None for the API call
                actual_lang = None if lang.lower() in ["none", "any", "all"] else lang
                
                for r in RARITIES:
                    for d in DOMAINS:
                        print(f"Fetching: {r} {d} | Qty: {q} | Zero: {z} | Lang: {actual_lang}")
                        
                        # Call the calculation logic
                        result = calculate_cost(r, d, q, z, actual_lang)
                        
                        if "error" not in result and result.get("count", 0) > 0:
                            save_price(
                                r, d, q, z, actual_lang, None,
                                result["total_cost"], 
                                result["items_found"], 
                                result["count"], 
                                result["currency"]
                            )
                            print(f"  Saved: {result['total_cost']} {result['currency']}")
                            total_updates += 1
                        else:
                            reason = result.get("error") or "No cards matching criteria"
                            print(f"  Skipped: {reason}")
                        
                        # Be nice to the API
                        time.sleep(1.5)

    print(f"\nUpdate complete. Total records added: {total_updates}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cron script to update Riftbound prices.")
    
    # Allow multiple values for each flag
    parser.add_argument("-q", "--quantities", type=int, nargs="+", default=[1], 
                        help="List of quantities to update (e.g. -q 1 3 4)")
    
    parser.add_argument("-l", "--languages", type=str, nargs="+", default=["en"], 
                        help="List of languages to update (e.g. -l en fr none)")
    
    # Use 0 and 1 for boolean flags in list format
    parser.add_argument("-z", "--zero", type=int, nargs="+", default=[1], 
                        help="List of Zero-only statuses (1 for True, 0 for False. e.g. -z 0 1)")

    args = parser.parse_args()
    
    # Convert 0/1 back to Booleans
    zero_bools = [bool(val) for val in args.zero]
    
    run_update(args.quantities, zero_bools, args.languages)