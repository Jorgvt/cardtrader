import sqlite3
from datetime import datetime, timedelta

DB_NAME = "prices.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rarity TEXT,
            domain TEXT,
            quantity INTEGER,
            zero_only BOOLEAN,
            language TEXT,
            expansion TEXT,
            foil BOOLEAN DEFAULT 0,
            price REAL,
            items_found INTEGER,
            total_cards INTEGER,
            currency TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration for existing DBs
    try:
        cursor.execute('ALTER TABLE price_history ADD COLUMN foil BOOLEAN DEFAULT 0')
    except sqlite3.OperationalError:
        pass # Already exists
        
    conn.commit()
    conn.close()

def save_price(rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO price_history 
        (rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (rarity, domain, quantity, zero_only, language, expansion, price, items_found, total_cards, currency, foil))
    conn.commit()
    conn.close()

def get_latest_price(rarity, domain, quantity, zero_only, language, expansion, foil=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    lang_filter = "language IS ?" if language else "language IS NULL"
    exp_filter = "expansion IS ?" if expansion else "expansion IS NULL"
    
    query = f'''
        SELECT * FROM price_history 
        WHERE rarity = ? AND domain = ? AND quantity = ? AND zero_only = ? AND foil = ?
        AND {lang_filter} AND {exp_filter}
        ORDER BY timestamp DESC LIMIT 1
    '''
    
    params = [rarity, domain, quantity, zero_only, foil]
    if language: params.append(language)
    if expansion: params.append(expansion)
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_latest(quantity, zero_only, language, expansion, foil=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    lang_filter = "language IS ?" if language else "language IS NULL"
    exp_filter = "expansion IS ?" if expansion else "expansion IS NULL"
    
    query = f'''
        SELECT rarity, domain, price, items_found, total_cards, currency, timestamp, foil
        FROM price_history p1
        WHERE timestamp = (
            SELECT MAX(timestamp) 
            FROM price_history p2 
            WHERE p1.rarity = p2.rarity AND p1.domain = p2.domain
            AND quantity = ? AND zero_only = ? AND foil = ? AND {lang_filter} AND {exp_filter}
        )
        AND quantity = ? AND zero_only = ? AND foil = ? AND {lang_filter} AND {exp_filter}
    '''
    
    p = [quantity, zero_only, foil]
    if language: p.append(language)
    if expansion: p.append(expansion)
    params = p + p 
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]