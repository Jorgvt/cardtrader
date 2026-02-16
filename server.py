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
REFRESH_COOLDOWN_HOURS = 1 # Cooldown for fresh API calls

@app.on_event("startup")
def startup_event():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "rarities": RARITIES,
        "domains": DOMAINS
    })

@app.get("/api/price")
async def get_price(
    rarity: str, 
    domain: str, 
    q: int = 1, 
    z: bool = False, 
    l: str = None, 
    e: str = None,
    force_refresh: bool = False
):
    # 1. Check latest in DB
    # Handle empty strings from JS as None
    lang = l if l else None
    exp = e if e else None
    
    latest = db.get_latest_price(rarity, domain, q, z, lang, exp)
    
    if latest and not force_refresh:
        return dict(latest)

    # 2. Check cooldown if force_refresh is requested
    if latest and force_refresh:
        # SQLite returns UTC timestamps usually, depending on implementation. 
        # For simplicity, we compare time.
        last_time = datetime.strptime(latest['timestamp'], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() - last_time < timedelta(hours=REFRESH_COOLDOWN_HOURS):
            return {
                "error": f"Cooldown active. Last update was {latest['timestamp']}",
                "cached": dict(latest)
            }

    # 3. Call API and save
    result = calc.calculate_cost(rarity, domain, q, z, lang, exp)
    
    if "error" not in result and result.get("count", 0) > 0:
        db.save_price(
            rarity, domain, q, z, lang, exp,
            result["total_cost"], result["items_found"], result["count"], result["currency"]
        )
        # Fetch it back to get the timestamp from DB
        latest = db.get_latest_price(rarity, domain, q, z, lang, exp)
        return dict(latest)
    
    return result

@app.get("/api/latest")
async def get_all_latest(q: int = 1, z: bool = False, l: str = None, e: str = None):
    lang = l if l else None
    exp = e if e else None
    return db.get_all_latest(q, z, lang, exp)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)