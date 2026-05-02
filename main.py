import os
import logging
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time
from functools import wraps

app = Flask(__name__)

# ——— Config ———
BOT_TOKEN       = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID         = os.environ["TELEGRAM_CHAT_ID"]
WEBHOOK_SECRET  = os.environ.get("WEBHOOK_SECRET", "change-me-now")
TELEGRAM_URL    = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Rate-limit: max 1 identical msg per 15s ( TradingView may fire many times )
_recent = {}

def dedup_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ——— Helpers ———
def send_telegram(text: str) -> bool:
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        r.raise_for_status()
        app.logger.info("Telegram OK | %s", text[:60].replace("\n", " "))
        return True
    except Exception as e:
        app.logger.error("Telegram FAIL: %s", e)
        return False

# ——— Routes ———
@app.route("/")
def health():
    return jsonify({"status": "ok", "service": "tv-telegram-bridge"}), 200

@app.route("/webhook/<secret>", methods=["POST"])
def webhook(secret):
    if secret != WEBHOOK_SECRET:
        app.logger.warning("Bad secret from %s", request.remote_addr)
        return "Unauthorized", 401

    # TradingView sends plain text or JSON depending on alert config
    raw = request.get_data(as_text=True)
    if not raw or not raw.strip():
        return "Empty", 200

    # TradingView webhooks often send JSON with "message" key when using
    # alert() with plain text. Detect and unwrap.
    msg = raw
    if request.is_json:
        data = request.get_json(silent=True) or {}
        msg = data.get("message", raw)

    # Deduplicate / rate-limit identical messages within 15s
    key = dedup_key(msg)
    now = time.time()
    if key in _recent and (now - _recent[key]) < 15:
        app.logger.info("Dedup dropped | %s", msg[:50])
        return "Dedup", 200
    _recent[key] = now
    # Cleanup old dedup entries
    cutoff = now - 60
    for k in list(_recent.keys()):
        if _recent[k] < cutoff:
            del _recent[k]

    ok = send_telegram(msg)
    return ("OK", 200) if ok else ("Fail", 502)

@app.route("/webhook/<secret>", methods=["GET"])
def webhook_probe(secret):
    """Coolify / uptime-kuma health probe for webhook path."""
    if secret != WEBHOOK_SECRET:
        return "Unauthorized", 401
    return "Ready", 200

# ——— Run ———
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)
