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
Finds cards where the cheapest listing is significantly lower (20%+) than the market floor.

**Usage:**
```bash
uv run find_cheap_cards.py <rarity> [language] [flags]
```

**Flags:**
- `-e, --expansion`: Expansion name (e.g., `origins`, `unleashed`) or ID. Default: `origins`.
- `-z, --zero`: Only include CardTrader Zero compatible listings.

---

### 2. Calculate Collection Cost (`calculate_collection_cost.py`)
Calculates the total cost to buy a set of cards filtered by rarity and domain.

**Usage:**
```bash
uv run calculate_collection_cost.py <rarity> <domain> [language] [flags]
```

**Flags:**
- `-e, --expansion`: Filter by expansion name (e.g., `origins`, `unleashed`) or code (`ogn`, `unl`).
- `-q, --quantity`: Number of copies of each card (default: 1).
- `-z, --zero`: Only include CardTrader Zero compatible listings.

---

---

---

### 5. Automated Updates (`cron_update.py`)
A script intended for use with a cronjob to update the database automatically. It accepts multiple values for each filter to update several configurations in one run.

**Manual Run Example:**
```bash
# Update for quantities 1 and 3, in both English and French, Zero Only
uv run python cron_update.py --quantities 1 3 --languages en fr --zero 1
```

**Flags:**
- `-q, --quantities`: List of quantities (e.g., `1 3 4`).
- `-l, --languages`: List of language codes (e.g., `en fr`). Use `none` for "Any".
- `-z, --zero`: List of Zero-only statuses (`1` for True, `0` for False).

**Setting up a Cronjob:**
```cron
0 */6 * * * cd /path/to/project && /path/to/uv run python cron_update.py -q 1 3 -l en -z 1 >> /path/to/project/cron.log 2>&1
```




