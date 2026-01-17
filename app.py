from flask import Flask, render_template, request, jsonify
from bot import CopyBot
import os

app = Flask(__name__)

# Core Bot Instance Manager
bot_instance = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    """Returns the current operational status of the bot engine."""
    global bot_instance
    is_running = bot_instance is not None and bot_instance.running
    logs = bot_instance.logs if bot_instance else []
    return jsonify({
        "running": is_running,
        "logs": logs
    })

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Initializes and starts the copy trading engine."""
    global bot_instance
    data = request.json
    
    if bot_instance and bot_instance.running:
        return jsonify({"message": "PolyCopy Engine is already active."}), 400

    try:
        # Extract payload
        target = data.get('target')
        pk = data.get('private_key')
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        passphrase = data.get('passphrase')
        amount = data.get('amount')
        match_amount = data.get('match_amount', False)
        
        # Validation
        if not target or not pk:
            return jsonify({"message": "Target wallet and Private Key are mandatory."}), 400

        # Initialize instance
        bot_instance = CopyBot(
            target_wallet=target,
            private_key=pk,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=passphrase,
            amount_per_trade=amount,
            match_amount=match_amount
        )
        bot_instance.start()
        
        return jsonify({"message": "Deployment Successful"}), 200
    except Exception as e:
        app.logger.error(f"Boot error: {e}")
        return jsonify({"message": f"Hardware Failure: {str(e)}"}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Gracefully terminates the copy trading engine."""
    global bot_instance
    if bot_instance:
        bot_instance.stop()
        bot_instance = None
    return jsonify({"message": "Termination sequence complete."})

if __name__ == '__main__':
    # Print a nice startup banner
    print("-" * 30)
    print("   PolyCopy UI Server")
    print("   Status: Operational")
    print("-" * 30)
    app.run(debug=True, port=5000)
