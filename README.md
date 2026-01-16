# 🦅 Polymarket Copy Trading Bot

**Automate your profits.** Capture the moves of the smartest whales on Polymarket in real-time.

This high-performance Python bot monitors any target wallet and instantly replicates their trades on your account. Whether they are betting on breaking news, elections, or crypto prices, you'll be right there with them.

---

## 🚀 Key Features

*   **⚡ Instant Execution**: Detects and copies trades within seconds using the Polymarket Data API.
*   **🎯 Target Monitoring**:  Watch any specific wallet address (Whales, Insiders, Top Traders).
*   **💸 Smart Order Placement**: Uses aggressive Limit Orders to ensure your trade gets filled immediately (simulating Market Orders).
*   **🔒 Secure**: Your keys remain local. Direct interaction with the Polygon CLOB (Central Limit Order Book).
*   **⚙️ Fully Configurable**: Set your own trade size (USDC amount) and custom proxy credentials.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/alerodriargui/polymarket-copy-trading-bot
    cd polymarket-copy-trading-bot
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Configuration**:
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

4.  **Configure your keys**:
    Open `.env` and fill in your details:
    *   `target_wallet_address`: The wallet address you want to copy.
    *   `private_key`: Your Polygon wallet private key (Must have USDC & MATIC).
    *   `api_key`, `api_secret`, `api_passphrase`: Your Polymarket CLOB API credentials.
    *   `amount_per_trade`: How much USDC to bet per trade (e.g., 10).

## 🏃‍♂️ Usage

Start the bot and watch it work:

```bash
python bot.py
```

The bot will displaying "Monitoring wallet: 0x..." and print logs whenever a new trade is detected and copied.

---

## ⚠️ Disclaimer

**Use at your own risk.** accessing DeFi protocols and trading involves risk of financial loss. This software is provided "as is" without any warranty. High-frequency trading or copying loss-making wallets can result in loss of funds. Ensure you have enough MATIC for gas (if required) and USDC for trades.
