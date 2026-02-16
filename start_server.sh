#!/bin/bash
# Navigate to the script's directory
cd "$(dirname "$0")"

# Get port from argument or default to 8000
PORT=${1:-8000}

# Run the server using uv
uv run python server.py --port "$PORT"
