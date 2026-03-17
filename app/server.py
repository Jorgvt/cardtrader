from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
import re
from .core import database as db
from .games.riftbound import RiftboundGame
from .games.fab import FABGame

app = FastAPI()

# Setup templates path relative to project root
templates = Jinja2Templates(directory="app/templates")

# Register supported games
GAMES = {
    "riftbound": RiftboundGame(),
    "fab": FABGame()
}

@app.on_event("startup")
def startup_event():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Get game from query params manually to ensure it's captured
    game = request.query_params.get("game", "riftbound")
    
    if game not in GAMES:
        game = "riftbound"
    
    selected_game = GAMES[game]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_game": game,
        "games": list(GAMES.keys()),
        "rarities": selected_game.rarities,
        "domains": selected_game.domains,
        "expansions": [{"name": k, "code": k} for k in selected_game.expansions.keys()]
    })

@app.get("/api/fab/generate-list")
async def generate_fab_list(
    class_name: str,
    rarity: str,
    expansion: str = None,
    quantity: int = 1,
    deduplicate: bool = False
):
    game = GAMES.get("fab")
    if not game:
        raise HTTPException(status_code=404, detail="FAB game not found")
    
    type_mapping = game.load_cards_mapping()
    all_identities = sorted(type_mapping.keys(), key=len, reverse=True)
    
    expansions_to_check = {}
    if not expansion or expansion.lower() == 'all':
        expansions_to_check = game.expansions
    else:
        for exp_name, exp_id in game.expansions.items():
            if expansion.lower() == exp_name.lower() or expansion.lower() in exp_name.lower():
                expansions_to_check[exp_name] = exp_id
    
    if not expansions_to_check:
        return {"items": []}

    final_items = {}
    from .core import api
    
    exp_code_regex = re.compile(r'\s*\([^)]*[A-Z]{3,}[^)]*\)\s*')
    variant_regex = re.compile(r'\s*-\s*(unlimited|1st edition|rainbow foil|cold foil|foil).*', re.I)

    for exp_name, exp_id in expansions_to_check.items():
        try:
            blueprints = api.fetch_blueprints(exp_id)
            for bp in blueprints:
                # 1. Rarity Filter
                bp_rarity = bp.get('fixed_properties', {}).get('fab_rarity', '').lower()
                if bp_rarity != rarity.lower():
                    continue
                
                # 2. Identity Resolution
                bp_name = bp['name']
                norm_bp_name = game.normalize_name(bp_name)
                
                identity = None
                for ident in all_identities:
                    if norm_bp_name.startswith(ident):
                        identity = ident
                        break
                
                if not identity:
                    continue
                
                # 3. Class Filter
                card_types = type_mapping.get(identity, "")
                if class_name.lower() in card_types.lower():
                    # 4. Deduplication
                    if deduplicate and identity in final_items:
                        continue

                    # Store name and the blueprint ID for later cost estimation
                    clean_name = exp_code_regex.sub(' ', bp_name)
                    clean_name = variant_regex.sub('', clean_name).strip()
                    
                    final_items[identity] = {
                        "display_name": f"{quantity}x {clean_name}",
                        "bp_id": bp['id'],
                        "name": bp_name,
                        "exp": exp_name
                    }
        except:
            continue
            
    # Sort by display name
    sorted_data = sorted(final_items.values(), key=lambda x: x['display_name'].split('x ', 1)[1])
    return {
        "items": [d['display_name'] for d in sorted_data],
        "blueprints": [{"id": d['bp_id'], "name": d['name']} for d in sorted_data]
    }

@app.post("/api/fab/estimate-cost")
async def estimate_fab_cost(
    request: Request
):
    body = await request.json()
    blueprint_ids = body.get("blueprint_ids", [])
    quantity = body.get("quantity", 1)
    zero_only = body.get("zero_only", False)
    
    game = GAMES.get("fab")
    if not game:
        raise HTTPException(status_code=404, detail="FAB game not found")

    total_cost_cents = 0
    from .core import api
    
    for bp_id in blueprint_ids:
        try:
            market_data = api.fetch_marketplace_products(bp_id)
            listings = market_data.get(str(bp_id), [])
            
            if zero_only:
                listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub')]
            
            listings = [l for l in listings if not l.get('graded') and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']]
            listings = [l for l in listings if not game.is_foil(l)]

            if listings:
                sorted_listings = sorted(listings, key=lambda x: x.get('price_cents', float('inf')))
                needed = quantity
                for l in sorted_listings:
                    price = l.get('price_cents', 0)
                    if price is None: continue
                    avail = l.get('quantity', 1)
                    to_take = min(avail, needed)
                    total_cost_cents += to_take * price
                    needed -= to_take
                    if needed <= 0: break
        except:
            continue
            
    return {
        "total_cost": total_cost_cents / 100,
        "currency": "EUR"
    }

@app.get("/api/{game_name}/price")
async def get_price(
    game_name: str,
    rarity: str, 
    domain: str, 
    q: int = 1, 
    z: bool = False, 
    l: str = None, 
    e: str = None,
    f: bool = False,
    force_refresh: bool = False
):
    if game_name not in GAMES:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = GAMES[game_name]
    lang = l if l and l.lower() != "none" else None
    exp = e if e and e.lower() != "none" else None
    
    # Inventory check
    inventory_path = f"data/{game_name}/collection.csv"
    use_inventory = os.path.exists(inventory_path)
    
    if not use_inventory:
        latest = db.get_latest_price(game_name, rarity, domain, q, z, lang, exp, f)
        if latest and not force_refresh:
            return dict(latest)

    # Call game-specific calculation
    result = game.calculate_collection_cost(rarity, domain, q, z, lang, exp, f, use_inventory)
    
    if "error" not in result and result.get("count", 0) > 0:
        if not use_inventory:
            db.save_price(
                game_name, rarity, domain, q, z, lang, exp,
                result["total_cost"], result["items_found"], result["count"], result["currency"], f,
                result.get("items")
            )
            # Re-fetch from DB to get the JSON-parsed version + timestamp
            latest = db.get_latest_price(game_name, rarity, domain, q, z, lang, exp, f)
            return dict(latest)
        else:
            # If using inventory, return results directly (not cached)
            return result

@app.get("/api/{game_name}/latest")
async def get_all_latest(game_name: str, q: int = 1, z: bool = False, l: str = None, e: str = None, f: bool = False):
    if game_name not in GAMES:
        raise HTTPException(status_code=404, detail="Game not found")
    
    inventory_path = f"data/{game_name}/collection.csv"
    if os.path.exists(inventory_path):
        return []
    
    lang = l if l and l.lower() != "none" else None
    exp = e if e and e.lower() != "none" else None
    return db.get_all_latest(game_name, q, z, lang, exp, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
