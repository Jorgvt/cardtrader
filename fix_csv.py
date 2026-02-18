import csv

def fix_csv():
    header = ["ID", "Name", "V1", "V2", "V3", "V4", "V5", "Energy", "Might", "Power", "Card Type", "Rarity", "Domain", "Tags", "Ability", "Image URL"]
    
    rows = []
    with open('cards.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0] == "ID": continue
            # Ensure row has exactly 16 columns
            if len(row) < 16:
                row.extend([""] * (16 - len(row)))
            elif len(row) > 16:
                row = row[:16]
            rows.append(row)
            
    with open('cards.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    print(f"Fixed cards.csv. Total cards: {len(rows)}")

if __name__ == "__main__":
    fix_csv()
