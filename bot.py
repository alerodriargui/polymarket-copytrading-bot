import os
import time
import requests
import logging
import threading
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from eth_account import Account

# Define a custom logger to capture logs for the UI
class ListHandler(logging.Handler):
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_list.append(msg)
            if len(self.log_list) > 100: # Keep last 100 lines
                self.log_list.pop(0)
        except Exception:
            self.handleError(record)

# Configuration
ACTIVITY_API = "https://data-api.polymarket.com/activity"

class CopyBot:
    def __init__(self, target_wallet, private_key, api_key, api_secret, api_passphrase, amount_per_trade, chain_id=137, host="https://clob.polymarket.com"):
        self.target_wallet = target_wallet
        self.private_key = private_key
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.amount_per_trade = float(amount_per_trade)
        self.chain_id = int(chain_id)
        self.host = host
        
        self.running = False
        self.logs = []
        
        # Setup Logger
        self.logger = logging.getLogger(f"Bot_{id(self)}")
        self.logger.setLevel(logging.INFO)
        # Clear existing handlers
        self.logger.handlers = []
        handler = ListHandler(self.logs)
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also console
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        self.logger.addHandler(console)
        
        self.client = None

    def get_client(self):
        try:
            return ClobClient(
                host=self.host,
                key=self.private_key,
                chain_id=self.chain_id,
                creds={
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                    "api_passphrase": self.api_passphrase
                }
            )
        except Exception as e:
            self.logger.error(f"Error creating client: {e}")
            return None

    def fetch_activity(self, limit=10):
        try:
            params = {
                "user": self.target_wallet,
                "limit": limit,
            }
            resp = requests.get(ACTIVITY_API, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Error fetching activity: {e}")
            return []

    def calculate_size_and_price(self, token_id, side):
        try:
            midpoint = self.client.get_midpoint(token_id)
            if not midpoint: midpoint = 0.5
            current_price = float(midpoint)
            
            if current_price <= 0.01: current_price = 0.01
            if current_price >= 0.99: current_price = 0.99
            
            size = self.amount_per_trade / current_price
            size = round(size, 2)
            
            if side == "BUY":
                price = 0.99
            else:
                price = 0.01
                
            return size, price
        except Exception as e:
            self.logger.error(f"Error calculating size: {e}")
            return 0, 0

    def execute_copy_trade(self, trade_data):
        try:
            side = trade_data.get('side', '').upper()
            token_id = trade_data.get('asset')
            if not token_id:
                self.logger.warning(f"No token_id found in trade")
                return

            self.logger.info(f"Detected: {side} {trade_data.get('title', 'Unknown')} ({trade_data.get('outcome')})")
            
            my_side = OrderType.BUY if side == "BUY" else OrderType.SELL
            size, price = self.calculate_size_and_price(token_id, side)
            
            if size <= 0:
                self.logger.warning("Size 0, skipping.")
                return

            self.logger.info(f"Placing Order: {side} {size} @ {price}")
            
            order_args = OrderArgs(
                price=price,
                size=size,
                side=my_side,
                token_id=token_id
            )
            
            resp = self.client.create_order(order_args)
            self.logger.info(f"Executed! ID: {resp.get('orderID', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Failed to copy: {e}")

    def run_loop(self):
        self.logger.info("Bot Started.")
        self.client = self.get_client()
        if not self.client:
            self.logger.error("Failed to initialize client. Stopping.")
            self.running = False
            return

        try:
            acct = Account.from_key(self.private_key)
            self.logger.info(f"Wallet: {acct.address}")
        except:
            self.logger.warning("Could not derive wallet address")

        last_hash = None
        
        # Init
        initial = self.fetch_activity(limit=1)
        if initial:
            last_hash = initial[0].get('transactionHash')
            self.logger.info(f"Initial Sync: {last_hash}")
        
        while self.running:
            try:
                time.sleep(2)
                activity = self.fetch_activity(limit=5)
                if not activity: continue
                
                new_items = []
                for item in activity:
                    if item.get('transactionHash') == last_hash:
                        break
                    new_items.append(item)
                
                if not new_items: continue
                
                for item in reversed(new_items):
                    # Check type
                    t_type = item.get('type')
                    if t_type in ['TRADE', 'OrderFilled']:
                         self.execute_copy_trade(item)
                    
                    last_hash = item.get('transactionHash')
            except Exception as e:
                self.logger.error(f"Loop error: {e}")
                time.sleep(5)
        
        self.logger.info("Bot Stopped.")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.run_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False

# For backward compatibility / CLI
if __name__ == "__main__":
    load_dotenv()
    # Configuration
    TARGET_WALLET = os.getenv("target_wallet_address")
    PRIVATE_KEY = os.getenv("private_key")
    API_KEY = os.getenv("CLOB_API_KEY") or os.getenv("api_key")
    API_SECRET = os.getenv("CLOB_API_SECRET") or os.getenv("api_secret")
    API_PASSPHRASE = os.getenv("CLOB_API_PASSPHRASE") or os.getenv("api_passphrase")
    AMOUNT = os.getenv("amount_per_trade", 10)
    
    bot = CopyBot(TARGET_WALLET, PRIVATE_KEY, API_KEY, API_SECRET, API_PASSPHRASE, AMOUNT)
    bot.start()
    
    try:
        while True:
            time.sleep(1)
            # Print logs to stdout
            # (Handled by StreamHandler in init)
    except KeyboardInterrupt:
        bot.stop()
