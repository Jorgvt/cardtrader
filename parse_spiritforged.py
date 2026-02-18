import csv
import re

def parse_sfd():
    cards = []
    
    # Range mappings for Domains in Spiritforged
    # Fury: 001-030
    # Calm: 031-060
    # Mind: 061-090
    # Body: 091-120
    # Chaos: 121-150
    # Order: 151-180
    # Legend/Misc: 181+
    
    def get_domain(n):
        if 1 <= n <= 30: return "Fury"
        if 31 <= n <= 60: return "Calm"
        if 61 <= n <= 90: return "Mind"
        if 91 <= n <= 120: return "Body"
        if 121 <= n <= 150: return "Chaos"
        if 151 <= n <= 180: return "Order"
        return "Colorless"

    with open('spiritforged_raw.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            # Look at columns that contain card-like IDs (3 digits + optional letters)
            # and next column for name
            for i in range(len(row) - 1):
                cell = row[i].strip()
                if re.match(r'^\d{3}[a-z]*$', cell):
                    name = row[i+1].strip()
                    if name and len(name) > 3 and "Page" not in name:
                        num_str = re.sub(r'\D', '', cell)
                        if not num_str: continue
                        num = int(num_str)
                        
                        # Skip if it's too high (token/misc not in set)
                        if num > 300: continue
                        
                        # Heuristic for rarity
                        rarity = "Common"
                        if 80 < num <= 140: rarity = "Uncommon"
                        elif 140 < num <= 213: rarity = "Rare"
                        elif num > 213: rarity = "Epic"
                        
                        # Avoid duplicates
                        if any(c['Name'] == name for c in cards): continue
                        
                        cards.append({
                            "ID": f"sfd-{cell}",
                            "Name": name,
                            "Rarity": rarity,
                            "Domain": get_domain(num)
                        })

    if not cards:
        print("No cards parsed.")
        return

    # Filter out duplicates and formatting artifacts
    # (Sometimes 'Against the Odds' appears with 001 and 001F)
    unique_cards = {}
    for c in cards:
        # Prefer the base number over the 'F' (foil) version for the ID
        base_id = re.sub(r'F$', '', c['ID'])
        if base_id not in unique_cards:
            unique_cards[base_id] = c
            unique_cards[base_id]['ID'] = base_id

    print(f"Parsed {len(unique_cards)} unique Spiritforged cards.")
    
    with open('cards.csv', 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for c in unique_cards.values():
            writer.writerow([c['ID'], c['Name'], "", "", "", "", "", "", "", "", "", c['Rarity'], c['Domain'], "", "", ""])
    
    print("Appended to cards.csv")

if __name__ == "__main__":
    parse_sfd()