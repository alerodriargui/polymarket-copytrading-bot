# 🦅 PolyCopy - Polymarket Copy Trading Bot

**Steal the Alpha.** Capture the moves of the smartest whales on Polymarket in real-time with a sleek, easy-to-use Web Dashboard.

This tool monitors any target wallet and instantly replicates their trades on your account using the Polygon CLOB for maximum speed.

---

## ⚡ Features

*   **🖥️ Web Dashboard**: A premium, dark-mode UI to configure and monitor your bot without touching code.
*   **🚀 Instant Execution**: Detects and copies trades milliseconds after they happen.
*   **🎯 Target Monitoring**: Watch any specific wallet address (Whales, Insiders, Top Traders).
*   **💸 Smart & Aggressive**: Uses optimized Limit Orders (Buy @ 0.99 / Sell @ 0.01) to ensure immediate fills.
*   **🔒 Secure**: Your keys remain local. No middleman servers.
*   **⚙️ Fully Configurable**: Adjust trade size and target wallet on the fly.

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

3.  **Setup Configuration (Optional for CLI, unnecessary for Web)**:
    Copy the example environment file if you plan to run headless:
    ```bash
    cp .env.example .env
    ```

## 🏃‍♂️ Usage

### Option 1: Web Interface (Recommended)
The easiest way to use the bot.

1.  Start the web server:
    ```bash
    python app.py
    ```
2.  Open your browser and navigate to:
    **`http://127.0.0.1:5000`**

3.  Enter your **Private Key**, **Target Wallet**, and **Amount**, then click **Start**.

### Option 2: Command Line (Headless)
Best for servers or advanced users.

1.  Edit your `.env` file with your credentials.
2.  Run the bot:
    ```bash
    python bot.py
    ```

## ☁️ Deployment

You can deploy this on any cloud provider (Render, Railway, Heroku) to run 24/7.
*   **Build Command**: `pip install -r requirements.txt`
*   **Start Command**: `gunicorn app:app`

## ⚠️ Disclaimer

**Use at your own risk.** accessing DeFi protocols and trading involves risk of financial loss. This software is provided "as is" without any warranty. High-frequency trading or copying loss-making wallets can result in loss of funds. 
