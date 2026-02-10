# CardTrader Riftbound Tools

A collection of Python scripts to interact with the CardTrader API for the Riftbound TCG.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) for dependency management.
- A CardTrader API token.

## Setup

1. Create an `env` file in the root directory.
2. Add your API token:
   ```env
   API_CARDTRADER="your_token_here"
   ```

## Scripts

### 1. Find Cheap Cards (`find_cheap_cards.py`)
Finds cards where the cheapest listing is significantly lower (20%+) than the market floor (average of the next 5 cheapest listings).

**Usage:**
```bash
uv run find_cheap_cards.py <rarity> [language] [flags]
```

**Example:**
```bash
uv run find_cheap_cards.py Epic en --zero
```

**Arguments:**
- `rarity`: Epic, Rare, Common, etc.
- `language`: (Optional) en, fr, etc.
- `-z, --zero`: Only include CardTrader Zero compatible listings.
- `-e, --expansion`: Expansion ID (default: 4166 for Origins).

---

### 2. Calculate Collection Cost (`calculate_collection_cost.py`)
Calculates the total cost to buy a set of cards filtered by rarity and domain from `cards.csv`. It accounts for availability and buys from the next cheapest seller if stock is low.

**Usage:**
```bash
uv run calculate_collection_cost.py <rarity> <domain> [language] [flags]
```

**Example:**
```bash
uv run calculate_collection_cost.py Epic Fury en --quantity 3 --zero
```

**Arguments:**
- `rarity`: Epic, Rare, Common, etc.
- `domain`: Fury, Calm, Mind, Body, Chaos, Order.
- `language`: (Optional) en, fr, etc.
- `-q, --quantity`: Number of copies of each card (default: 1).
- `-z, --zero`: Only include CardTrader Zero compatible listings.

---

### 3. Fetch Wishlists (`fetch_wishlists.py`)
Fetches all your CardTrader wishlists and saves their contents into individual text files in the `wishlists_content/` directory.

**Usage:**
```bash
uv run fetch_wishlists.py
```
