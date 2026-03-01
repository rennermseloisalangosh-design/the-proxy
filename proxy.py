import requests
import logging
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# YOUR BOT TOKEN
BOT_TOKEN = "8429527897:AAFyS5FgnCARPbF3UwOb0S4Jp37PwzjiXj8"

# File for proxy storage
PROXY_FILE = "proxies.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_proxies():
    """Load all saved proxies."""
    if os.path.exists(PROXY_FILE):
        try:
            with open(PROXY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_proxy(proxy_data):
    """Save proxy to persistent storage."""
    proxies = load_proxies()
    proxy_key = f"{proxy_data['ip']}:{proxy_data['port']}"
    proxies[proxy_key] = proxy_data
    with open(PROXY_FILE, 'w') as f:
        json.dump(proxies, f, indent=2)

def test_proxy(ip, port, username=None, password=None):
    """Advanced proxy testing with full diagnostics."""
    proxy_url = f"http://{ip}:{port}"
    proxies = {'http': proxy_url, 'https': proxy_url}
    
    if username and password:
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        proxies = {'http': proxy_url, 'https': proxy_url}
    
    try:
        # Test 1: Basic connectivity
        resp1 = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=12)
        origin_ip = resp1.json().get('origin', 'Unknown')
        
        # Test 2: HTTPS support
        resp2 = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=12)
        
        # Test 3: Speed test
        start_time = datetime.now()
        resp3 = requests.get('http://httpbin.org/get', proxies=proxies, timeout=10)
        speed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Country lookup
        country_data = requests.get(f"http://ip-api.com/json/{origin_ip}?fields=status,country,countryCode,regionName,city,isp", timeout=8).json()
        country = country_data.get('country', 'Unknown')
        country_code = country_data.get('countryCode', '?')
        isp = country_data.get('isp', 'Unknown')
        
        return {
            'live': True,
            'status_code': resp1.status_code,
            'origin_ip': origin_ip,
            'country': country,
            'country_code': country_code,
            'isp': isp,
            'speed_ms': round(speed_ms, 1),
            'https_support': resp2.status_code == 200
        }
    except Exception as e:
        return {'live': False, 'error': str(e)[:100], 'status_code': getattr(e.response, 'status_code', None)}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main welcome screen."""
    proxies = load_proxies()
    proxy_count = len(proxies)
    
    welcome = "PROXY CHECKER PRO\n\n"
    welcome += f"Saved Proxies: {proxy_count}\n"
    welcome += "Commands:\n"
    welcome += "/c - Check default proxy\n"
    welcome += "/t - Test proxy (new format)\n"
    welcome += "/check - Check proxy with auth\n"
    welcome += "/list - Saved proxies\n"
    welcome += "/help - Guide\n\n"
    welcome += "Try /t command!"
    
    await update.message.reply_text(welcome)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help."""
    help_text = """PROXY CHECKER PRO GUIDE

=== /t COMMAND (NEW FORMAT) ===

Format: /t IP PORT [USERNAME] [PASSWORD]

Examples:
/t 186.97.236.242 5685 admin holi
/t 1.2.3.4 8080
/t 103.49.202.252 80

If no username/password, just skip them:
/t IP PORT

=== /check COMMAND ===

Format: /check IP PORT [USER] [PASS]

Examples:
/check 1.2.3.4 8080
/check 1.2.3.4 8080 myuser mypass

=== DEFAULT PROXY ===
/c - Check 103.49.202.252:80

=== OTHER COMMANDS ===
/list - Saved proxies
/recent - Recent 5 proxies
/help - This guide"""
    await update.message.reply_text(help_text)

async def check_default_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check the default proxy 103.49.202.252:80"""
    ip = "103.49.202.252"
    port = "80"
    
    await update.message.reply_text(f"Testing {ip}:{port}...")
    
    result = test_proxy(ip, int(port))
    
    # Save result
    proxy_data = {
        'ip': ip,
        'port': port,
        'tested_at': datetime.now().isoformat(),
        'result': result
    }
    save_proxy(proxy_data)
    
    if result['live']:
        msg = f"""PROXY LIVE!

Proxy: {ip}:{port}
Real IP: {result['origin_ip']}
Country: {result['country']} ({result['country_code']})
ISP: {result['isp'][:30]}
Speed: {result['speed_ms']}ms
HTTPS: {'Yes' if result['https_support'] else 'No'}
Status: {result['status_code']}

Ready for use!"""
    else:
        msg = f"""PROXY DEAD!

Proxy: {ip}:{port}
Error: {result.get('error', 'Connection failed')}
Status: {result.get('status_code', 'N/A')}

Try another proxy!"""
    
    await update.message.reply_text(msg)

# NEW /t COMMAND
async def test_proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test proxy using /t command format: /t ip port [user] [pass]"""
    try:
        args = context.args
        
        if len(args) < 2:
            await update.message.reply_text("""/t COMMAND FORMAT:

/t IP PORT [USERNAME] [PASSWORD]

Examples:
/t 186.97.236.242 5685 admin holi
/t 1.2.3.4 8080
/t 103.49.202.252 80

If no auth: /t IP PORT
With auth: /t IP PORT USER PASS""")
            return
        
        ip = args[0]
        port = args[1]
        username = args[2] if len(args) > 2 else None
        password = args[3] if len(args) > 3 else None
        
        # Validate IP format
        parts = ip.split('.')
        if len(parts) != 4:
            await update.message.reply_text("Invalid IP format!")
            return
        
        # Validate port
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            await update.message.reply_text("Invalid port! Use 1-65535")
            return
        
        auth_info = ""
        if username and password:
            auth_info = f" | User: {username} | Pass: {password}"
        
        await update.message.reply_text(f"Testing {ip}:{port}{auth_info}...")
        
        result = test_proxy(ip, int(port), username, password)
        
        # Save result
        proxy_data = {
            'ip': ip,
            'port': port,
            'username': username,
            'password': password,
            'tested_at': datetime.now().isoformat(),
            'result': result
        }
        save_proxy(proxy_data)
        
        if result['live']:
            msg = f"""✅ PROXY LIVE!

🌐 Proxy: {ip}:{port}"""
            if username and password:
                msg += f"\n👤 Auth: {username}:{password}"
            msg += f"""
📍 Real IP: {result['origin_ip']}
🌍 Country: {result['country']} ({result['country_code']})
🏢 ISP: {result['isp'][:30]}
⚡ Speed: {result['speed_ms']}ms
🔒 HTTPS: {'Yes' if result['https_support'] else 'No'}
📊 Status: {result['status_code']}

Ready for use!"""
        else:
            msg = f"""❌ PROXY DEAD!

🌐 Proxy: {ip}:{port}"""
            if username and password:
                msg += f"\n👤 Auth: {username}:{password}"
            msg += f"""
❌ Error: {result.get('error', 'Connection failed')}
📊 Status: {result.get('status_code', 'N/A')}

Try another proxy!"""
        
        await update.message.reply_text(msg)
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def check_custom_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check custom proxy with /check command"""
    try:
        args = context.args
        
        if len(args) < 2:
            await update.message.reply_text("""Usage:
/check ip port - Without auth
/check ip port user pass - With auth

Examples:
/check 1.2.3.4 8080
/check 1.2.3.4 8080 myuser mypass""")
            return
        
        ip = args[0]
        port = args[1]
        username = args[2] if len(args) > 2 else None
        password = args[3] if len(args) > 3 else None
        
        # Validate IP format
        parts = ip.split('.')
        if len(parts) != 4:
            await update.message.reply_text("Invalid IP format!")
            return
        
        # Validate port
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            await update.message.reply_text("Invalid port! Use 1-65535")
            return
        
        auth_info = ""
        if username and password:
            auth_info = f" (User: {username})"
        
        await update.message.reply_text(f"Testing {ip}:{port}{auth_info}...")
        
        result = test_proxy(ip, int(port), username, password)
        
        # Save result
        proxy_data = {
            'ip': ip,
            'port': port,
            'username': username,
            'password': password,
            'tested_at': datetime.now().isoformat(),
            'result': result
        }
        save_proxy(proxy_data)
        
        if result['live']:
            msg = f"""PROXY LIVE!

Proxy: {ip}:{port}"""
            if username and password:
                msg += f"\nAuth: {username}:{password}"
            msg += f"""
Real IP: {result['origin_ip']}
Country: {result['country']} ({result['country_code']})
ISP: {result['isp'][:30]}
Speed: {result['speed_ms']}ms
HTTPS: {'Yes' if result['https_support'] else 'No'}
Status: {result['status_code']}

Ready for use!"""
        else:
            msg = f"""PROXY DEAD!

Proxy: {ip}:{port}"""
            if username and password:
                msg += f"\nAuth: {username}:{password}"
            msg += f"""
Error: {result.get('error', 'Connection failed')}
Status: {result.get('status_code', 'N/A')}

Try another proxy!"""
        
        await update.message.reply_text(msg)
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def list_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show saved proxies."""
    proxies = load_proxies()
    if not proxies:
        await update.message.reply_text("No saved proxies. Use /t or /check to add!")
        return
    
    message = "SAVED PROXIES:\n\n"
    for i, (key, data) in enumerate(list(proxies.items())[-10:], 1):
        result = data['result']
        status = "LIVE" if result['live'] else "DEAD"
        auth = ""
        if data.get('username'):
            auth = " (Auth)"
        message += f"{i}. {key}{auth} - {status} {result.get('country', '?')}\n"
    
    await update.message.reply_text(message)

async def recent_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent proxies."""
    proxies = load_proxies()
    if not proxies:
        await update.message.reply_text("No proxies checked yet.")
        return
    
    recent = sorted(proxies.items(), key=lambda x: x[1].get('tested_at', ''), reverse=True)[:5]
    message = "RECENT PROXIES:\n\n"
    for key, data in recent:
        result = data.get('result', {})
        status = "LIVE" if result.get('live') else "DEAD"
        message += f"{key} - {status}\n"
    
    await update.message.reply_text(message)

def main():
    """Run the bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("c", check_default_proxy))
    app.add_handler(CommandHandler("t", test_proxy_command))  # NEW /t COMMAND
    app.add_handler(CommandHandler("check", check_custom_proxy))
    app.add_handler(CommandHandler("list", list_proxies))
    app.add_handler(CommandHandler("recent", recent_proxies))
    
    # Check if running on Render (cloud) or local
    webhook_url = os.environ.get("WEBHOOK_URL")
    
    if webhook_url:
        # Use webhook mode for cloud deployment (Render)
        print(f"Running in WEBHOOK mode: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)),
            url_path="webhook",
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Use polling mode for local development
        print("Bot started! Press Ctrl+C to stop.")
        print("Use /t command for new format!")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
