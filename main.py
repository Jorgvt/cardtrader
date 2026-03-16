import uvicorn
import argparse
from app.server import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CardTrader Hub Dashboard.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    args = parser.parse_args()
    
    # We run the app imported from app.server
    uvicorn.run(app, host="0.0.0.0", port=args.port)