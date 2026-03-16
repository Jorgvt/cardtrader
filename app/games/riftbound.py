import csv
import os
import re
from .base import BaseGame
from ..core import api

class RiftboundGame(BaseGame):
    @property
    def name(self):
        return "riftbound"

    @property
    def rarities(self):
        return ["Common", "Uncommon", "Rare", "Epic"]

    @property
    def domains(self):
        return ["Fury", "Calm", "Mind", "Body", "Chaos", "Order"]

    @property
    def expansions(self):
        return {
            "Origins": 4166,
            "Promos": 4167,
            "Proving Grounds": 4275,
            "Organized Play": 4287,
            "Judge Promos": 4288,
            "Arcane": 4289,
            "Spiritforged": 4299,
            "SFD": 4299, # Mapping both just in case
            "Championship Promo": 4347,
            "Nexus Night Promos": 4348,
            "Release Event Promos": 4349,
            "Unleashed": 4425
        }

    def normalize_name(self, name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def is_foil(self, listing):
        props = listing.get('properties_hash', {})
        return props.get('riftbound_foil') or props.get('foil')

    def get_domain_property_name(self):
        # Riftbound uses domain in the CSV but filters in marketplace might be different
        # Actually for Riftbound we filter the CSV items, not the API listings by domain property
        return None

    def load_inventory(self):
        inventory = {}
        path = "data/riftbound/collection.csv"
        if not os.path.exists(path):
            return inventory
        
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Name')
                    qty = row.get('Quantity', 0)
                    if name:
                        inventory[self.normalize_name(name)] = int(qty)
        except Exception as e:
            print(f"Error loading inventory: {e}")
        return inventory

    def calculate_collection_cost(self, rarity_target, domain_target, quantity=1, zero_only=False, lang_target=None, expansion_filter=None, foil_target=False, use_inventory=False):
        inventory = self.load_inventory() if use_inventory else None
        
        cards_to_buy = []
        path = "data/riftbound/cards.csv"
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['Rarity'].lower() != rarity_target.lower(): continue
                    card_domains = [d.strip().lower() for d in row['Dominion'].split(',')]
                    if domain_target.lower() not in card_domains: continue
                    if expansion_filter and row['Set'].lower() != expansion_filter.lower(): continue
                    
                    target_qty = quantity
                    if inventory:
                        owned_qty = inventory.get(self.normalize_name(row['Name']), 0)
                        target_qty = max(0, quantity - owned_qty)
                    
                    if target_qty > 0:
                        row['_needed_qty'] = target_qty
                        cards_to_buy.append(row)
        except Exception as e:
            return {"error": f"Error reading cards.csv: {str(e)}"}

        if not cards_to_buy:
            return {"count": 0, "total_cost": 0, "found_count": 0, "items_found": 0, "currency": "EUR"}

        total_cost_cents = 0
        found_count = 0
        total_items_found = 0
        currency = "EUR"
        blueprint_cache = {}
        items_list = [] # List of {name, qty, price, link}

        for card in cards_to_buy:
            card_name = card['Name']
            norm_name = self.normalize_name(card_name)
            set_name = card['Set']
            exp_id = self.expansions.get(set_name)
            if not exp_id: continue

            if exp_id not in blueprint_cache:
                try:
                    blueprint_cache[exp_id] = api.fetch_blueprints(exp_id)
                except: continue

            target_bp = None
            for bp in blueprint_cache.get(exp_id, []):
                if self.normalize_name(bp['name']) == norm_name:
                    if bp.get('version') in [None, '']:
                        target_bp = bp
                        break
                    target_bp = bp
            
            if not target_bp: continue

            try:
                market_data = api.fetch_marketplace_products(target_bp['id'])
                listings = market_data.get(str(target_bp['id']), [])
            except: continue

            if zero_only:
                listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub')]

            listings = [l for l in listings if not l.get('graded') and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']]

            if lang_target:
                listings = [l for l in listings if l.get('properties_hash', {}).get('riftbound_language', '').lower() == lang_target.lower()]

            if foil_target:
                listings = [l for l in listings if self.is_foil(l)]
            else:
                non_foils = [l for l in listings if not self.is_foil(l)]
                if non_foils: listings = non_foils

            if not listings: continue

            sorted_listings = sorted(listings, key=lambda x: x.get('price_cents', float('inf')))
            needed = card['_needed_qty']
            card_total = 0
            card_found = 0
            
            for l in sorted_listings:
                price = l.get('price_cents')
                if price is None: continue
                avail = l.get('quantity', 1)
                to_take = min(avail, needed)
                card_total += to_take * price
                needed -= to_take
                card_found += to_take
                currency = l.get('price_currency', currency)
                if needed <= 0: break
            
            if card_found > 0:
                total_cost_cents += card_total
                total_items_found += card_found
                found_count += 1
                items_list.append({
                    "name": card_name,
                    "qty": card_found,
                    "price": card_total / 100,
                    "link": f"https://www.cardtrader.com/cards/{target_bp['id']}"
                })

        return {
            "rarity": rarity_target,
            "domain": domain_target,
            "count": len(cards_to_buy),
            "found_count": found_count,
            "items_found": total_items_found,
            "total_cost": total_cost_cents / 100,
            "currency": currency,
            "using_inventory": bool(inventory),
            "items": items_list
        }
