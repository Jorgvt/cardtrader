import sqlite3
import os
import json

DB_NAME = "prices.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT,
            rarity TEXT,
            domain TEXT,
            quantity INTEGER,
            zero_only BOOLEAN,
            language TEXT,
            expansion TEXT,
            foil BOOLEAN,
            price REAL,
            items_found INTEGER,
            total_cards INTEGER,
            currency TEXT,
            items_json TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("PRAGMA table_info(price_history)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'game' not in columns:
        cursor.execute('ALTER TABLE price_history ADD COLUMN game TEXT')
    if 'foil' not in columns:
        cursor.execute('ALTER TABLE price_history ADD COLUMN foil BOOLEAN DEFAULT 0')
    if 'items_json' not in columns:
        cursor.execute('ALTER TABLE price_history ADD COLUMN items_json TEXT')

    conn.commit()
    conn.close()

def save_price(game, rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil=False, items=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    items_json = json.dumps(items) if items else None
    cursor.execute('''
        INSERT INTO price_history 
        (game, rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil, items_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (game, rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil, items_json))
    conn.commit()
    conn.close()

def get_latest_price(game, rarity, domain, quantity, zero_only, language, expansion, foil=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    lang_filter = "language IS ?" if language else "language IS NULL"
    exp_filter = "expansion IS ?" if expansion else "expansion IS NULL"
    
    query = f'''
        SELECT * FROM price_history 
        WHERE game = ? AND rarity = ? AND domain = ? AND quantity = ? AND zero_only = ? AND foil = ?
        AND {lang_filter} AND {exp_filter}
        ORDER BY timestamp DESC LIMIT 1
    '''
    
    params = [game, rarity, domain, quantity, zero_only, foil]
    if language: params.append(language)
    if expansion: params.append(expansion)
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get('items_json'):
            d['items'] = json.loads(d['items_json'])
        return d
    return None

def get_all_latest(game, quantity, zero_only, language, expansion, foil=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    lang_filter = "language IS ?" if language else "language IS NULL"
    exp_filter = "expansion IS ?" if expansion else "expansion IS NULL"
    
    query = f'''
        SELECT rarity, domain, price, items_found, total_cards, currency, timestamp, foil, items_json
        FROM price_history p1
        WHERE game = ? AND timestamp = (
            SELECT MAX(timestamp) 
            FROM price_history p2 
            WHERE p1.game = p2.game AND p1.rarity = p2.rarity AND p1.domain = p2.domain
            AND quantity = ? AND zero_only = ? AND foil = ? AND {lang_filter} AND {exp_filter}
        )
        AND quantity = ? AND zero_only = ? AND foil = ? AND {lang_filter} AND {exp_filter}
    '''
    
    p = [quantity, zero_only, foil]
    if language: p.append(language)
    if expansion: p.append(expansion)
    params = [game] + p + p 
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        if d.get('items_json'):
            d['items'] = json.loads(d['items_json'])
        results.append(d)
    return results