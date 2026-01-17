import os
import time
import requests
import logging
import threading
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from eth_account import Account

# Custom logger for UI integration
class ListHandler(logging.Handler):
    def __init__(self, log_list: List[str]):
        super().__init__()
        self.log_list = log_list

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.log_list.append(msg)
            if len(self.log_list) > 200:
                self.log_list.pop(0)
        except Exception:
            self.handleError(record)

# Constants
ACTIVITY_API = "https://data-api.polymarket.com/activity"

class CopyBot:
    """
    PolyCopy Engine: Replicates Polymarket trades in real-time.
    """
    def __init__(
        self, 
        target_wallet: str, 
        private_key: str, 
        api_key: str, 
        api_secret: str, 
        api_passphrase: str, 
        amount_per_trade: Any, 
        match_amount: bool = False, 
        chain_id: int = 137, 
        host: str = "https://clob.polymarket.com"
    ):
        self.target_wallet = target_wallet.lower()
        self.private_key = private_key
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.amount_per_trade = float(amount_per_trade) if amount_per_trade else 10.0
        self.match_amount = match_amount
        self.chain_id = chain_id
        self.host = host
        
        self.running = False
        self.logs: List[str] = []
        
        # Initialize internal logger
        self.logger = logging.getLogger(f"PolyCopy_{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        
        # UI Handler
        ui_handler = ListHandler(self.logs)
        ui_handler.setFormatter(formatter)
        self.logger.addHandler(ui_handler)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self.client: Optional[ClobClient] = None
        self.processed_transactions = set()

    def get_client(self) -> Optional[ClobClient]:
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
            self.logger.error(f"Client Init Failed: {e}")
            return None

    def fetch_activity(self, limit: int = 20) -> List[Dict]:
        try:
            params = {"user": self.target_wallet, "limit": limit}
            resp = requests.get(ACTIVITY_API, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            # self.logger.error(f"Sync error: {e}")
            return []

    def calculate_trade_metrics(self, trade_data: Dict, side: str):
        try:
            token_id = trade_data.get('asset')
            if not token_id:
                return 0, 0
            
            # Fetch midpoint and handle various response formats
            mid_resp = self.client.get_midpoint(token_id)
            if isinstance(mid_resp, dict):
                # Some API versions return a dict like {"midpoint": 0.5} 
                # or an error dict {"error": "...", "status": ...}
                mid_val = mid_resp.get('midpoint')
                if mid_val is not None:
                    current_price = float(mid_val)
                else:
                    current_price = 0.5
            else:
                current_price = float(mid_resp) if mid_resp else 0.5
            
            # Safeguards
            current_price = max(0.01, min(0.99, current_price))
            
            amount_to_spend = self.amount_per_trade
            if self.match_amount:
                target_usdc = trade_data.get('usdcSize')
                if target_usdc is not None:
                    try:
                        # Ensure target_usdc is treated as a number
                        if isinstance(target_usdc, (int, float, str)):
                            amount_to_spend = float(target_usdc)
                            self.logger.info(f"Target spend detected: ${amount_to_spend:.2f}")
                        else:
                            self.logger.warning(f"Unexpected usdcSize type ({type(target_usdc)}): {target_usdc}. Using default.")
                    except (ValueError, TypeError):
                        self.logger.warning(f"Could not parse usdcSize: {target_usdc}. Using default.")
                else:
                    self.logger.warning("Target amount missing from activity, using fallback.")
            
            size = round(amount_to_spend / current_price, 2)
            # Market order simulation via limit price
            exec_price = 0.99 if side == "BUY" else 0.01
                
            return size, exec_price
        except Exception as e:
            self.logger.error(f"Metrics calc failed: {e}. Token ID: {trade_data.get('asset')}")
            return 0, 0

    def process_copy_trade(self, trade_data: Dict):
        try:
            side = trade_data.get('side', '').upper()
            token_id = trade_data.get('asset')
            title = trade_data.get('title', 'Unknown Market')
            outcome = trade_data.get('outcome', 'Unknown')
            
            if not token_id:
                return

            self.logger.info(f"Signal Detected: {side} '{title}' -> {outcome}")
            
            size, price = self.calculate_trade_metrics(trade_data, side)
            if size <= 0:
                self.logger.warning("Calculated size invalid, skipping.")
                return

            self.logger.info(f"Propagating Order: {side} {size} shares @ ${price}")
            
            order_args = OrderArgs(
                price=price,
                size=size,
                side=OrderType.BUY if side == "BUY" else OrderType.SELL,
                token_id=token_id
            )
            
            resp = self.client.create_order(order_args)
            order_id = resp.get('orderID', 'FAILED')
            
            if order_id != 'FAILED':
                self.logger.info(f"Order Executed Successfully! ID: {order_id[:8]}...")
            else:
                self.logger.error(f"Execution response: {resp}")
            
        except Exception as e:
            self.logger.error(f"Replication failed: {e}")

    def run_loop(self):
        self.logger.info("Initializing PolyCopy Engine...")
        self.client = self.get_client()
        if not self.client:
            self.running = False
            return

        try:
            acct = Account.from_key(self.private_key)
            self.logger.info(f"Active Wallet: {acct.address[:10]}...{acct.address[-4:]}")
        except:
            self.logger.warning("Private key valid, but address derivation failed.")

        # Initial state sync to avoid processing history
        initial = self.fetch_activity(limit=20)
        for item in initial:
            t_hash = item.get('transactionHash')
            if t_hash:
                self.processed_transactions.add(t_hash)
        
        self.logger.info(f"Synced with {len(self.processed_transactions)} historical transactions.")
        self.logger.info("Listening for signals on Polymarket...")
        
        while self.running:
            try:
                activity = self.fetch_activity(limit=10)
                if not activity:
                    time.sleep(2)
                    continue
                
                new_items = []
                for item in activity:
                    t_hash = item.get('transactionHash')
                    if t_hash and t_hash in self.processed_transactions:
                        continue
                    if not t_hash:
                        continue
                    new_items.append(item)
                
                if new_items:
                    # Process from oldest to newest
                    for item in reversed(new_items):
                        if item.get('type') in ['TRADE', 'OrderFilled']:
                            self.process_copy_trade(item)
                        
                        t_hash = item.get('transactionHash')
                        if t_hash:
                            self.processed_transactions.add(t_hash)
                    
                    # Memory management
                    if len(self.processed_transactions) > 100:
                        hashes = list(self.processed_transactions)
                        self.processed_transactions = set(hashes[-100:])
                
                time.sleep(2)
                    
            except Exception as e:
                # self.logger.error(f"Loop error: {e}")
                time.sleep(5)
        
        self.logger.info("Engine Shutdown complete.")

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

if __name__ == "__main__":
    load_dotenv()
    # CLI mode fallback
    bot = CopyBot(
        os.getenv("target_wallet_address", ""),
        os.getenv("private_key", ""),
        os.getenv("api_key", ""),
        os.getenv("api_secret", ""),
        os.getenv("api_passphrase", ""),
        os.getenv("amount_per_trade", 10),
        os.getenv("match_amount", "false").lower() == "true"
    )
    bot.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
