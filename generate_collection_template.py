import csv

def generate_template():
    source_file = 'riftbound_cards_by_set.csv'
    template_file = 'collection_template.csv'
    
    cards = []
    try:
        with open(source_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cards.append({
                    "Name": row['Name'],
                    "Rarity": row['Rarity'],
                    "Dominion": row['Dominion'],
                    "Set": row['Set'],
                    "Quantity": 0
                })
    except Exception as e:
        print(f"Error reading source: {e}")
        return

    # Sort by Set, then Dominion, then Name
    cards.sort(key=lambda x: (x['Set'], x['Dominion'], x['Name']))

    header = ["Name", "Rarity", "Dominion", "Set", "Quantity"]
    with open(template_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(cards)
    
    print(f"Successfully generated {template_file} with {len(cards)} cards.")

if __name__ == "__main__":
    generate_template()
