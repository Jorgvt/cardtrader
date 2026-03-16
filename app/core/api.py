import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path='env')
API_TOKEN = os.getenv('API_CARDTRADER')

def get_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def fetch_blueprints(expansion_id):
    url = "https://api.cardtrader.com/api/v2/blueprints/export"
    response = requests.get(url, headers=get_headers(), params={"expansion_id": expansion_id})
    response.raise_for_status()
    return response.json()

def fetch_marketplace_products(blueprint_id):
    url = "https://api.cardtrader.com/api/v2/marketplace/products"
    response = requests.get(url, headers=get_headers(), params={"blueprint_id": blueprint_id})
    response.raise_for_status()
    return response.json()

def fetch_wishlists():
    url = "https://api.cardtrader.com/api/v2/wishlists"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def fetch_wishlist_details(wishlist_id):
    url = f"https://api.cardtrader.com/api/v2/wishlists/{wishlist_id}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()
