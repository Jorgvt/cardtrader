#!/bin/bash
# Navigate to the script's directory
cd "$(dirname "$0")"

# Run the server using uv
uv run python server.py
