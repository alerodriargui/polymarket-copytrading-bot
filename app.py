from flask import Flask, render_template, request, jsonify
from bot import CopyBot
import os

app = Flask(__name__)

# Global Bot Instance
# For a simple local app, a single global instance is fine.
bot_instance = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    global bot_instance
    isRunning = bot_instance is not None and bot_instance.running
    logs = bot_instance.logs if bot_instance else []
    # Reverse logs to show newest first? Or frontend handles it.
    return jsonify({
        "running": isRunning,
        "logs": logs
    })

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_instance
    data = request.json
    
    if bot_instance and bot_instance.running:
        return jsonify({"message": "Bot already running"}), 400

    try:
        target = data.get('target')
        pk = data.get('private_key')
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        passphrase = data.get('passphrase')
        amount = data.get('amount')
        
        bot_instance = CopyBot(target, pk, api_key, api_secret, passphrase, amount)
        bot_instance.start()
        
        return jsonify({"message": "Bot Started"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_instance
    if bot_instance:
        bot_instance.stop()
        bot_instance = None
    return jsonify({"message": "Bot Stopped"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
