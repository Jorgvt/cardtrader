import time
import argparse
from app.games.riftbound import RiftboundGame
from app.core import database as db

def run_update(game_name, quantities, zero_only, languages):
    """
    Iterates through combinations and updates the database.
    """
    db.init_db()
    
    if game_name == "riftbound":
        game = RiftboundGame()
    else:
        print(f"Game {game_name} not supported for cron yet.")
        return

    total_updates = 0
    print(f"Starting automated update for {game_name}...")
    
    for q in quantities:
        for z in zero_only:
            for lang in languages:
                actual_lang = None if lang.lower() in ["none", "any", "all"] else lang
                
                for r in game.rarities:
                    for d in game.domains:
                        print(f"Fetching: {r} {d} | Qty: {q} | Zero: {z} | Lang: {actual_lang}")
                        
                        result = game.calculate_collection_cost(r, d, q, z, actual_lang)
                        
                        if "error" not in result and result.get("count", 0) > 0:
                            db.save_price(
                                game_name, r, d, q, z, actual_lang, None,
                                result["total_cost"], 
                                result["items_found"], 
                                result["count"], 
                                result["currency"]
                            )
                            print(f"  Saved: {result['total_cost']} {result['currency']}")
                            total_updates += 1
                        else:
                            print(f"  Skipped: {result.get('error', 'No cards found')}")
                        
                        time.sleep(1.5)

    print(f"\nUpdate complete. Total records added: {total_updates}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cron script to update card prices.")
    parser.add_argument("-g", "--game", default="riftbound", help="Game name (default: riftbound)")
    parser.add_argument("-q", "--quantities", type=int, nargs="+", default=[1])
    parser.add_argument("-l", "--languages", type=str, nargs="+", default=["en"])
    parser.add_argument("-z", "--zero", type=int, nargs="+", default=[1])

    args = parser.parse_args()
    zero_bools = [bool(val) for val in args.zero]
    run_update(args.game, args.quantities, zero_bools, args.languages)
