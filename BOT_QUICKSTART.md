# Telegram Bot - Quick Start Guide

## Prerequisites

1. **Install dependencies** (if not already installed):
```bash
pip install psutil python-telegram-bot
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

2. **Configure bot token** in `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALLOWED_USERS=   # Leave empty for all users
```

## Option 1: Simple Start (Recommended)

**No extra dependencies needed - works immediately:**

```bash
python start_bot_simple.py
```

This will:
- ✅ Clear pending updates automatically
- ✅ Start the bot in foreground
- ✅ Show logs in real-time
- ✅ Stop with Ctrl+C

## Option 2: Advanced Start (with psutil)

**Requires psutil - better process management:**

```bash
python restart_bot.py
```

This will:
- ✅ Kill any old bot processes
- ✅ Clear pending updates
- ✅ Start fresh bot instance
- ✅ Show startup logs

**To stop:**
```bash
python restart_bot.py --stop
```

## Option 3: Direct Start

**Minimal - just run the bot:**

```bash
python -m telegram_interface.bot
```

⚠️ **Warning**: If bot was running before, you may have pending updates. Use Option 1 or 2 instead.

## Testing the Bot

### In Telegram App:
1. Open Telegram
2. Search for: `@lawercasebot`
3. Send: `/start`
4. You should receive immediate response!

### Available Commands:
```
/start              - Welcome message
/help               - Help information
/ask <question>     - Ask MegaAgent
/case_get <id>      - Get case info
/memory_lookup <q>  - Search memory
/generate_letter <t> - Generate letter
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'psutil'"
**Solution:**
```bash
pip install psutil
# OR use simple starter:
python start_bot_simple.py
```

### Bot doesn't respond
**Solution:**
```bash
# Stop all bots
python restart_bot.py --stop
# OR manually:
# Find and kill python processes running telegram_interface.bot

# Clear updates
python test_bot_interaction.py

# Start fresh
python start_bot_simple.py
```

### "Access denied" in Telegram
**Solution:**
- Get your Telegram user ID (use @userinfobot)
- Add to `.env`: `TELEGRAM_ALLOWED_USERS=your_user_id`
- Or leave empty for public access: `TELEGRAM_ALLOWED_USERS=`

### Check bot status
```bash
python test_bot_interaction.py
```

Shows:
- ✅ Bot connectivity
- 📊 Pending updates count
- 📨 Recent messages
- 🌐 Webhook status

## Recommended Workflow

### Development:
```bash
# Start bot
python start_bot_simple.py

# In another terminal - check status
python test_bot_interaction.py

# Stop with Ctrl+C
```

### Production:
```bash
# Use process manager (systemd, supervisor, PM2)
# Or run with nohup:
nohup python -m telegram_interface.bot > bot.log 2>&1 &
```

## Quick Reference

| Script | Purpose | Needs psutil? |
|--------|---------|---------------|
| `start_bot_simple.py` | Quick start | ❌ No |
| `restart_bot.py` | Advanced management | ✅ Yes |
| `test_bot_interaction.py` | Diagnostics | ❌ No |
| `python -m telegram_interface.bot` | Direct run | ❌ No |

## Bot Information

- **Username**: @lawercasebot
- **Bot ID**: 7472625853
- **API Version**: python-telegram-bot 22.5
- **Status**: ✅ Operational

## Next Steps

After bot is running:
1. ✅ Test all commands
2. ✅ Check response times
3. ✅ Monitor logs for errors
4. ✅ Test with real users

## Support

If issues persist:
1. Check logs for errors
2. Verify `.env` configuration
3. Test bot connectivity with `test_bot_interaction.py`
4. Review [TELEGRAM_BOT_DIAGNOSIS.md](TELEGRAM_BOT_DIAGNOSIS.md) for detailed troubleshooting
