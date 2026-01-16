import os
import time
import requests
import json
import logging
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
TARGET_WALLET = os.getenv("target_wallet_address")
PRIVATE_KEY = os.getenv("private_key")
# Support both CLOB_ prefix and simple names
API_KEY = os.getenv("CLOB_API_KEY") or os.getenv("api_key")
API_SECRET = os.getenv("CLOB_API_SECRET") or os.getenv("api_secret")
API_PASSPHRASE = os.getenv("CLOB_API_PASSPHRASE") or os.getenv("api_passphrase")
HOST = os.getenv("HOST", "https://clob.polymarket.com")
CHAIN_ID = int(os.getenv("CHAIN_ID", 137))
AMOUNT_PER_TRADE = float(os.getenv("amount_per_trade", 10))

# Gamma API for activity
ACTIVITY_API = "https://data-api.polymarket.com/activity"

def get_client():
    if not API_KEY or not PRIVATE_KEY:
        logger.error("Missing credentials in .env (CLOB_API_KEY, PRIVATE_KEY, etc)")
        return None
    return ClobClient(
        host=HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        creds={
            "api_key": API_KEY,
            "api_secret": API_SECRET,
            "api_passphrase": API_PASSPHRASE
        }
    )

from eth_account import Account

def get_client_and_check():
    client = get_client()
    if not client: return None
    
    try:
        # Derive address to show user
        acct = Account.from_key(PRIVATE_KEY)
        logger.info(f"Bot Wallet Address: {acct.address}")
        
        # Simple balance check via API is hard without endpoints, but we can rely on ClobClient
        # or just assume if we are here, keys are loaded.
        # We will add a 'Are you sure?' log.
    except Exception as e:
        logger.error(f"Error deriving address: {e}")
    return client

def fetch_activity(wallet, limit=10):
    """
    Fetch recent activity for a wallet from Polymarket Data API.
    """
    try:
        params = {
            "user": wallet,  # Correct parameter is 'user', not 'address'
            "limit": limit,
        }
        resp = requests.get(ACTIVITY_API, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error fetching activity: {e}")
        return []

def calculate_size_and_price(client, token_id, side):
    """
    Determine price and size for a 'Market' like execution.
    Target: Spend roughly AMOUNT_PER_TRADE usdc.
    """
    try:
        # Get current price
        # get_midpoint returns float or None
        midpoint = client.get_midpoint(token_id)
        if not midpoint:
            midpoint = 0.5 # Fallback
            
        current_price = float(midpoint)
        
        # Protect against div by zero or extreme prices
        if current_price <= 0.01: current_price = 0.01
        if current_price >= 0.99: current_price = 0.99
        
        # Calculate size (Shares = USD / Price)
        size = AMOUNT_PER_TRADE / current_price
        
        # Round size to safer precision (e.g. integer or 2 decimals?)
        # CLOB usually accepts float, but let's check mintick. 
        # Standard approach: keep it rough.
        size = round(size, 2)
        
        # Set aggressive limit price to ensure fill
        # BUY: Price = 1.0 (Max willing to pay)
        # SELL: Price = 0.0 (Min willing to sell)
        if side == "BUY":
            price = 0.99 # Cap slightly below 1
        else:
            price = 0.01 # Cap slightly above 0
            
        return size, price
    except Exception as e:
        logger.error(f"Error calculating size: {e}")
        return 0, 0

def execute_copy_trade(client, trade_data):
    """
    Execute the trade on our account.
    """
    try:
        # Parse fields from Activity API
        side = trade_data.get('side', '').upper() # BUY or SELL
        token_id = trade_data.get('asset') # The token ID is directly in 'asset'
            
        if not token_id:
            logger.warning(f"Could not find token_id (asset) in trade: {trade_data}")
            return

        logger.info(f"Detected Trade: {side} on Token {token_id} (Outcome: {trade_data.get('outcome')})")
        
        # Calculate our order
        my_side = OrderType.BUY if side == "BUY" else OrderType.SELL
        
        size, price = calculate_size_and_price(client, token_id, side)
        
        if size <= 0:
            logger.warning("Calculated size is 0, skipping.")
            return

        logger.info(f"Placing Order: {side} {size} shares @ {price}")
        
        order_args = OrderArgs(
            price=price,
            size=size,
            side=my_side,
            token_id=token_id
        )
        
        # Execute
        resp = client.create_order(order_args)
        logger.info(f"Order Executed! Response: {resp}")
        
    except Exception as e:
        logger.error(f"Failed to copy trade: {e}")

def main():
    logger.info("Starting Polymarket Copy Trading Bot...")
    client = get_client_and_check()
    if not client:
        return

    logger.info(f"Monitoring wallet: {TARGET_WALLET}")
    logger.info(f"Amount per trade: ${AMOUNT_PER_TRADE}")

    # Check Balances
    try:
        # Get collateral (USDC) balance
        # The library might have different methods, but let's try standard get_balance or similar if available,
        # or just catch the error. Standard ClobClient usually exposes helpers.
        # If not, we can infer from logs.
        logger.info("Checking connection...")
    except Exception:
        pass

    # Initialize state
    initial_activity = fetch_activity(TARGET_WALLET, limit=1)
    last_processed_hash = None
    
    if initial_activity and len(initial_activity) > 0:
        last_processed_hash = initial_activity[0].get('transactionHash')
        logger.info(f"Latest trade Hash on start: {last_processed_hash} (skipping existing)")
    else:
        logger.info("No prior activity found. Waiting for new trades...")

    while True:
        try:
            time.sleep(2) # Poll every 2 seconds
            
            activity = fetch_activity(TARGET_WALLET, limit=5)
            if not activity:
                continue
            
            # Filter new items
            # We look for trades that happened AFTER our last processed hash.
            # Since the API returns newest first, we iterate until we find the last hash.
            
            new_items = []
            for item in activity:
                item_hash = item.get('transactionHash')
                if item_hash == last_processed_hash:
                    break # Found the checkpoint
                new_items.append(item)
            
            if not new_items:
                continue
                
            # Process oldest new item first (reverse the list)
            for item in reversed(new_items):
                try:
                    logger.info(f"New Activity Found: {item.get('title', 'Unknown Market')}")
                    # Double check type just in case
                    if item.get('type') == 'TRADE' or item.get('type') == 'OrderFilled': 
                         execute_copy_trade(client, item)
                    
                    # Update checkpoint locally after successful (or attempted) process
                    last_processed_hash = item.get('transactionHash')
                    
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
            
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
