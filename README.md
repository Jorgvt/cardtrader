# CardTrader Multi-Game Hub

A modular collection of tools to track card prices, find deals, and manage inventories across multiple TCGs using the CardTrader API. Currently supporting **Riftbound** and **Flesh and Blood (FAB)**.

## Project Structure

- `app/core/`: Shared logic for API and Database.
- `app/games/`: Game-specific implementations (Riftbound, FAB).
- `data/`: CSV data and user collections organized by game.
- `templates/`: Dashboard UI.

## Setup

1. **API Key**: Create an `env` file in the root:
   ```env
   API_CARDTRADER="your_token_here"
   ```
2. **Dependencies**:
   ```bash
   uv sync
   ```

## Features

### 1. Multi-Game Dashboard
A FastAPI web server that displays a grid of collection prices.
- **Run**: `uv run python main.py --port 8000` (or use `./start_server.sh 8000`)
- **URL**: `http://localhost:8000`
- **Features**: Filter by Game, Rarity, Domain/Class, Language, and Foiling. Supports "Zero Only" listings and respects your local inventory.

### 2. Automated Price Updates
A script to update the price database via cronjob.
- **Manual Run**:
  ```bash
  uv run python cron_update.py --game riftbound --quantities 1 3 --languages en --zero 1
  ```
- **Cronjob Example**:
  ```cron
  0 */6 * * * cd /path/to/project && /path/to/uv run python cron_update.py -g fab -q 1 -z 1 >> /path/to/project/cron_fab.log 2>&1
  ```

### 3. Inventory Management
Track what you own to see only the cost of "missing" cards.
- **Riftbound**: Edit `data/riftbound/collection.csv`. Use `collection_template.csv` as a starting point.
- **FAB**: Support for `data/fab/collection.csv` (uses `Name, Quantity`).

### 4. Legacy / Utility Scripts
The root directory contains several utility scripts for specific tasks:
- `find_cheap_cards.py`: Snipe underpriced listings (Riftbound optimized).
- `fetch_wishlists.py`: Export your CardTrader wishlists to text files.
- `generate_collection_template.py`: Create a blank inventory CSV for Riftbound.

## Supported Games

- **Riftbound**: Full set tracking (Origins, SFD, etc.) using `riftbound_cards_by_set.csv`.
- **Flesh and Blood**: Class/Talent based tracking using `fab-cards.csv` mapping.
