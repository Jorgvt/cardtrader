from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import calculate_collection_cost as calc
import database as db
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configuration
RARITIES = ["Common", "Uncommon", "Rare", "Epic"]
DOMAINS = ["Fury", "Calm", "Mind", "Body", "Chaos", "Order"]
EXPANSIONS = [
    {"name": "Origins", "code": "Origins"},
    {"name": "Proving Grounds", "code": "Proving Grounds"},
    {"name": "Spiritforged (SFD)", "code": "SFD"},
    {"name": "Arcane", "code": "Arcane"},
    {"name": "Unleashed", "code": "Unleashed"}
]

@app.on_event("startup")
def startup_event():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "rarities": RARITIES,
        "domains": DOMAINS,
        "expansions": EXPANSIONS
    })

@app.get("/api/price")
async def get_price(
    rarity: str, 
    domain: str, 
    q: int = 1, 
    z: bool = False, 
    l: str = None, 
    e: str = None,
    f: bool = False,
    force_refresh: bool = False
):
    # 1. Check latest in DB
    lang = l if l else None
    exp = e if e else None
    
    # Inventory check
    inventory = None
    if os.path.exists("collection.csv"):
        inventory = calc.load_inventory("collection.csv")
    
    # We only use cache if not using inventory, 
    # OR we could improve cache to store inventory-based results (complex)
    # For now, if inventory exists, we ignore cache to be safe
    if not inventory:
        latest = db.get_latest_price(rarity, domain, q, z, lang, exp, f)
        if latest and not force_refresh:
            return dict(latest)

    # 3. Call API and save
    result = calc.calculate_cost(rarity, domain, q, z, lang, exp, f, inventory)
    
    if "error" not in result and result.get("count", 0) > 0:
        # Only cache results if NOT using inventory
        if not inventory:
            db.save_price(
                rarity, domain, q, z, lang, exp,
                result["total_cost"], result["items_found"], result["count"], result["currency"], f
            )
            latest = db.get_latest_price(rarity, domain, q, z, lang, exp, f)
            return dict(latest)
    
    return result

@app.get("/api/latest")
async def get_all_latest(q: int = 1, z: bool = False, l: str = None, e: str = None, f: bool = False):
    if os.path.exists("collection.csv"):
        return [] # Don't load cached if using inventory, force live or separate cache
    
    lang = l if l else None
    exp = e if e else None
    return db.get_all_latest(q, z, lang, exp, f)

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Riftbound Price Dashboard server.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    args = parser.parse_args()
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)