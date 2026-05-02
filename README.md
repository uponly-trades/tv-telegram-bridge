# TV Telegram Bridge

TradingView webhook → Telegram bot relay for FVG (Fair Value Gap) alerts.

## What it does

Receives plain-text alerts from TradingView Pine Script (`alert()` function) and forwards them to a Telegram chat via Bot API.

## Env vars

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Chat / group ID |
| `WEBHOOK_SECRET` | Yes | URL path secret (`/webhook/<SECRET>`) |
| `PORT` | No | Defaults to 8080 |

## TradingView setup

1. Add the "Ranked FVG Imbalance Zones — Telegram Edition" indicator to your chart.
2. Create an alert on the indicator, choose **"Alert() function calls"**.
3. In Notifications → Webhook URL, enter:
   ```
   https://<YOUR_DOMAIN>/webhook/<WEBHOOK_SECRET>
   ```
4. Leave the Message box empty — the Pine Script `alert()` already contains the full message.

## Deploy

Built for Coolify / Docker:

```bash
docker build -t tv-telegram-bridge .
docker run -p 8080:8080 --env-file .env tv-telegram-bridge
```
