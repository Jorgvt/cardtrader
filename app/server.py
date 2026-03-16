from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
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