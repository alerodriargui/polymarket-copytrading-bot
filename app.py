from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from bot import CopyBot
from dotenv import load_dotenv
import os
import uuid
from secrets import token_hex

# Load environment variables (.env)
load_dotenv()

app = Flask(__name__)

# Configure Session to be multi-user capable
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", token_hex(16))
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Global Registry of Bot Instances
# key: user_id (session based), value: CopyBot instance
bot_registry = {}

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/api/status')
def status():
    """Returns the current operational status of the user's bot engine."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"running": False, "logs": []})
    
    bot = bot_registry.get(user_id)
    is_running = bot is not None and bot.running
    logs = bot.logs if bot else []
    
    return jsonify({
        "running": is_running,
        "logs": logs
    })

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Initializes and starts a unique copy trading engine for the user."""
    user_id = session.get('user_id')
    if not user_id:
        session['user_id'] = str(uuid.uuid4())
        user_id = session['user_id']
        
    data = request.json
    
    if user_id in bot_registry and bot_registry[user_id].running:
        return jsonify({"message": "Your PolyCopy Engine is already active."}), 400

    try:
        # Extract and sanitize payload
        target = data.get('target', '').strip()
        pk = data.get('private_key', '').strip()
        
        # UI inputs take precedence, then .env as fallback
        api_key = data.get('api_key', '').strip() or os.getenv("api_key")
        api_secret = data.get('api_secret', '').strip() or os.getenv("api_secret")
        passphrase = data.get('passphrase', '').strip() or os.getenv("api_passphrase")
        amount = data.get('amount')
        match_amount = data.get('match_amount', False)
        
        # Validation
        if not target or not pk:
            return jsonify({"message": "Target wallet and Private Key are mandatory."}), 400

        # Create user-specific instance
        bot = CopyBot(
            target_wallet=target,
            private_key=pk,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=passphrase,
            amount_per_trade=amount,
            match_amount=match_amount
        )
        bot.start()
        
        # Register the bot
        bot_registry[user_id] = bot
        
        return jsonify({"message": "Engine deployed for your session."}), 200
    except Exception as e:
        app.logger.error(f"Boot error: {e}")
        return jsonify({"message": f"Hardware Failure: {str(e)}"}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Gracefully terminates the user's specific engine."""
    user_id = session.get('user_id')
    if user_id in bot_registry:
        bot_registry[user_id].stop()
        # We keep the instance in registry for a bit so logs remain visible while stopped
        # but the thread itself will die.
    return jsonify({"message": "Termination sequence complete."})

if __name__ == '__main__':
    # Print a nice startup banner
    print("-" * 40)
    print("   PolyCopy Multi-User Platform")
    print("   Status: Operational & Public Ready")
    print("-" * 40)
    app.run(debug=True, port=5000)
