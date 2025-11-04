# Telegram Bot Testing Guide

## Bot Information
- **Bot Username**: @lawercasebot
- **Bot ID**: 7472625853
- **Status**: ✅ Running and Ready for Testing

## Prerequisites
1. Telegram account
2. Bot token configured in `.env` file
3. User ID added to `TELEGRAM_ALLOWED_USERS` (if access control is enabled)

## How to Test

### 1. Start the Bot
```bash
python -m telegram_interface.bot
```

You should see output indicating the bot has started:
```
{"event": "telegram.bot.starting", "level": "info", ...}
Application started
```

### 2. Open Telegram and Find the Bot
- Open Telegram app (mobile or desktop)
- Search for `@lawercasebot`
- Click "Start" or send `/start`

### 3. Test Commands

#### Basic Commands
```
/start          - Get welcome message and command list
/help           - Show detailed help information
```

#### Agent Commands
```
/ask <question> - Ask the MegaAgent a question
Example: /ask What is an EB-1A visa?
```

#### Case Management
```
/case_get <case_id> - Get information about a specific case
Example: /case_get 12345
```

#### Memory & Search
```
/memory_lookup <query> - Search semantic memory
Example: /memory_lookup immigration law precedents
```

#### Document Generation
```
/generate_letter <title> - Generate a letter template
Example: /generate_letter Request for Evidence Response
```

### 4. Test Scenarios

#### Scenario 1: Welcome Flow
1. Send `/start`
2. Verify you receive welcome message in Russian with emoji
3. Check that all commands are listed

#### Scenario 2: Ask Question
1. Send `/ask What are the requirements for EB-1A?`
2. Wait for response from MegaAgent
3. Verify response is relevant and well-formatted

#### Scenario 3: Unauthorized Access (if enabled)
1. Try accessing from unauthorized user ID
2. Verify you receive "Access denied" message

#### Scenario 4: Conversational Mode
1. Send a plain text message (not a command)
2. Verify bot responds conversationally

## Expected Bot Behavior

### ✅ Success Indicators
- Bot responds within 5-10 seconds
- Messages are formatted in Markdown
- Russian text displays correctly with emoji
- Commands execute without errors
- Logs show successful handler execution

### ❌ Error Indicators
- No response after 30 seconds
- Python exceptions in logs
- "Access denied" for authorized users
- Malformed messages

## Common Issues

### Issue: Bot doesn't respond
**Solution**: Check that:
- Bot is running (`python -m telegram_interface.bot`)
- Token is correct in `.env`
- User ID is in allowed list (if configured)
- Check logs for errors

### Issue: "Access denied" message
**Solution**:
- Get your Telegram user ID (use @userinfobot)
- Add it to `TELEGRAM_ALLOWED_USERS` in `.env`
- Restart the bot

### Issue: Bot crashes on startup
**Solution**:
- Check all dependencies are installed
- Verify database connection (if required)
- Check logs for specific error messages

## Monitoring

### Watch Logs in Real-Time
```bash
# In one terminal - run bot
python -m telegram_interface.bot

# Bot outputs structured logs showing:
# - Incoming messages
# - Handler execution
# - Agent responses
# - Any errors
```

### Check Bot Status via Telegram API
```python
import requests
token = "YOUR_BOT_TOKEN"
url = f"https://api.telegram.org/bot{token}/getMe"
response = requests.get(url)
print(response.json())
```

## Test Results Template

```markdown
### Test Session: [Date/Time]
**Tester**: [Your Name]
**Bot Version**: [Commit SHA]

#### Tests Performed
- [ ] /start command
- [ ] /help command
- [ ] /ask command
- [ ] /case_get command
- [ ] /memory_lookup command
- [ ] /generate_letter command
- [ ] Plain text conversation
- [ ] Unauthorized access handling

#### Results
- Commands tested: X/8
- Success rate: X%
- Average response time: X seconds
- Errors encountered: [List any errors]

#### Notes
[Any additional observations]
```

## Advanced Testing

### Load Testing
Test bot with multiple concurrent users:
1. Create test script sending multiple requests
2. Monitor response times
3. Check for race conditions or errors

### Integration Testing
1. Test with real case data
2. Verify memory lookup returns relevant results
3. Test document generation end-to-end
4. Check error handling with invalid inputs

## Cleanup

When done testing:
```bash
# Stop the bot
Ctrl+C

# Check logs
cat bot_test.log
```

## Next Steps

After successful testing:
1. Document any bugs found
2. Test edge cases
3. Performance optimization if needed
4. Deploy to production environment
5. Set up monitoring and alerts
