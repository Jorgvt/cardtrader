import csv
import os
import re
from .base import BaseGame
from ..core import api

class FABGame(BaseGame):
    @property
    def name(self):
        return "fab"

    @property
    def rarities(self):
        return ["Token", "Common", "Rare", "Super Rare", "Majestic", "Legendary", "Fabled"]

    @property
    def domains(self):
        # These are Classes/Talents in FAB
        return ["Generic", "Brute", "Guardian", "Ninja", "Warrior", "Mechanologist", "Ranger", "Runeblade", "Wizard", "Illusionist", "Merchant", "Assassin", "Bard", "Brute", "Guardian", "Lightning", "Earth", "Ice", "Draconic", "Light", "Shadow", "Elemental"]

    @property
    def expansions(self):
        return {
            "WTR Unlimited": 2170,
            "ARC Unlimited": 2171,
            "CRU Unlimited": 2172,
            "MON Unlimited": 2173,
            "Tales of Aria": 2409,
            "Everfest": 2902,
            "History Pack 1": 3030,
            "Uprising": 3031,
            "Dynasty": 3130,
            "Outsiders": 3223,
            "Dusk till Dawn": 3362,
            "Bright Lights": 3465,
            "Heavy Hitters": 3559,
            "Part the Mistveil": 3737,
            "Rosetta": 3783,
            "The Hunted": 3938,
            "High Seas": 4116,
            "Compendium of Rathe": 4375
        }

    def normalize_name(self, name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def is_foil(self, listing):
        props = listing.get('properties_hash', {})
        # FAB uses 'foil' property usually
        return props.get('foil') or props.get('fab_foil')

    def get_domain_property_name(self):
        return None

    def load_cards_mapping(self):
        """Loads FAB CSV and maps card names (+ color) to their Types."""
        mapping = {}
        path = "data/fab/fab-cards.csv"
        if not os.path.exists(path):
            return mapping
        
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                # FAB CSV uses quotes and might have commas in fields
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Name')
                    color = row.get('Color')
                    types = row.get('Types', '')
                    
                    if not name: continue
                    
                    # Store by base name and by name-color
                    norm_name = self.normalize_name(name)
                    mapping[norm_name] = types
                    
                    if color:
                        norm_name_color = self.normalize_name(f"{name} {color}")
                        mapping[norm_name_color] = types
        except Exception as e:
            print(f"Error loading FAB cards: {e}")
        return mapping

    def calculate_collection_cost(self, rarity_target, domain_target, quantity=1, zero_only=False, lang_target=None, expansion_filter=None, foil_target=False, use_inventory=False):
        # 1. Load FAB database (mapping names to Types)
        type_mapping = self.load_cards_mapping()
        
        # 2. Fetch blueprints for selected expansion
        exp_id = self.expansions.get(expansion_filter)
        if not exp_id:
            return {"error": f"Expansion '{expansion_filter}' not found for FAB"}

        try:
            blueprints = api.fetch_blueprints(exp_id)
        except Exception as e:
            return {"error": f"Error fetching blueprints: {str(e)}"}

        # 3. Filter blueprints by Rarity and Domain
        target_blueprints = []
        for bp in blueprints:
            # Check rarity
            bp_rarity = bp.get('fixed_properties', {}).get('fab_rarity', '').lower()
            if bp_rarity != rarity_target.lower():
                continue
            
            # Check domain (Types) via name matching
            bp_name = bp['name']
            norm_bp_name = self.normalize_name(bp_name)
            
            # Try to find Types in our mapping
            card_types = type_mapping.get(norm_bp_name, "")
            if not card_types:
                # Try partial match or stripping " - Red" etc if mapping only has base name
                # Actually our mapping should have norm_name_color
                pass
            
            # Check if domain_target is in card_types
            # Domain target is e.g. "Ninja"
            if domain_target.lower() not in card_types.lower():
                continue
            
            target_blueprints.append(bp)

        if not target_blueprints:
            return {"count": 0, "total_cost": 0, "found_count": 0, "items_found": 0, "currency": "EUR"}

        total_cost_cents = 0
        found_count = 0
        total_items_found = 0
        currency = "EUR"
        items_list = []

        # 4. Fetch prices for each matched blueprint
        for bp in target_blueprints:
            try:
                market_data = api.fetch_marketplace_products(bp['id'])
                listings = market_data.get(str(bp['id']), [])
            except: continue

            if zero_only:
                listings = [l for l in listings if l.get('user', {}).get('can_sell_via_hub')]

            listings = [l for l in listings if not l.get('graded') and l.get('properties_hash', {}).get('condition') in ['Near Mint', 'Mint']]

            if lang_target:
                listings = [l for l in listings if l.get('properties_hash', {}).get('language', 'en').lower() == lang_target.lower()]

            if foil_target:
                listings = [l for l in listings if self.is_foil(l)]
            else:
                non_foils = [l for l in listings if not self.is_foil(l)]
                if non_foils: listings = non_foils

            if not listings: continue

            sorted_listings = sorted(listings, key=lambda x: x.get('price_cents', float('inf')))
            needed = quantity
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
                    "name": bp['name'],
                    "qty": card_found,
                    "price": card_total / 100,
                    "link": f"https://www.cardtrader.com/cards/{bp['id']}"
                })

        return {
            "rarity": rarity_target,
            "domain": domain_target,
            "count": len(target_blueprints),
            "found_count": found_count,
            "items_found": total_items_found,
            "total_cost": total_cost_cents / 100,
            "currency": currency,
            "using_inventory": False,
            "items": items_list
        }
