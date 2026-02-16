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
    {"name": "Origins", "code": "origins"},
    {"name": "Proving Grounds", "code": "proving_grounds"},
    {"name": "Arcane", "code": "arcane"},
    {"name": "Spiritforged", "code": "spiritforged"},
    {"name": "Unleashed", "code": "unleashed"}
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
    
    latest = db.get_latest_price(rarity, domain, q, z, lang, exp, f)
    
    if latest and not force_refresh:
        return dict(latest)

    # 3. Call API and save
    result = calc.calculate_cost(rarity, domain, q, z, lang, exp, f)
    
    if "error" not in result and result.get("count", 0) > 0:
        db.save_price(
            rarity, domain, q, z, lang, exp,
            result["total_cost"], result["items_found"], result["count"], result["currency"], f
        )
        latest = db.get_latest_price(rarity, domain, q, z, lang, exp, f)
        return dict(latest)
    
    return result

@app.get("/api/latest")
async def get_all_latest(q: int = 1, z: bool = False, l: str = None, e: str = None, f: bool = False):
    lang = l if l else None
    exp = e if e else None
    return db.get_all_latest(q, z, lang, exp, f)

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Riftbound Price Dashboard server.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    args = parser.parse_args()
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)