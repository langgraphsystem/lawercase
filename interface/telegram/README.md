# Mega Agent Pro Telegram Bot

Production-grade Telegram bot interface for Mega Agent Pro legal assistant system.

## Features

- **Case Management**: Create, select, and manage legal cases
- **Document Processing**: Upload and analyze documents with AI
- **Content Ingestion**: Learn from web pages, YouTube videos, and Telegram channels
- **AI Assistant**: Ask questions and get AI-powered answers with sources
- **Admin Tools**: System monitoring and management
- **Multi-language Support**: Russian and English interface

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and set required variables:
   ```bash
   cp .env.example .env
   ```

3. **Run the Bot**:
   ```bash
   python scripts/run_bot.py
   ```

## Environment Variables

### Required

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_ADMIN_USER_ID=123456789

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Vector Database
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENV=us-east-1-aws
PINECONE_INDEX=mega-agent-pro
VECTOR_DIM=1536

# LLM Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# S3 Storage
S3_BUCKET=mega-agent-documents
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_REGION=us-east-1
```

### Optional

```bash
# S3 Custom Endpoint (for S3-compatible services)
S3_ENDPOINT=https://s3.amazonaws.com

# File Upload Limits
MAX_FILE_MB=50
S3_PRESIGN_TTL_SECONDS=3600

# Telegram Ingestion (optional)
TG_API_ID=1234567
TG_API_HASH=abcdef1234567890abcdef1234567890
TG_SESSION_STRING=session_string_here

# Content Processing
WHISPER_MODEL=base
ALLOWED_DOMAINS=pravo.ru,consultant.ru,garant.ru

# LLM Configuration
LLM_PROVIDER_PRIORITY=openai,anthropic,gemini
LLM_DEFAULT_PROVIDER=openai
LLM_MAX_RETRIES=3
```

## Bot Commands

### Basic Commands

- `/start` - Welcome message and main menu
- `/help` - Show all available commands with examples

### Case Management

- `/case_new <title>` - Create new legal case
  - Example: `/case_new Дело о разводе Ивановых`
- `/case_use <case_id|title>` - Select active case for current chat
  - Example: `/case_use abc123` or `/case_use Дело о разводе`
- `/case_add [text]` - Add text, document, or image to active case
  - Text: `/case_add Important contract details...`
  - File: Send document with caption
  - Photo: Send image of document

### Content Learning

- `/learn_url <url> [params]` - Learn from web page
  - Example: `/learn_url https://pravo.ru/news/123 title="Legal News" tags="divorce,family" lang="ru"`
- `/learn_yt <url>` - Learn from YouTube video (subtitles/audio)
  - Example: `/learn_yt https://www.youtube.com/watch?v=abc123`
- `/learn_tg <@channel> [N]` - Learn from Telegram channel posts
  - Example: `/learn_tg @legalchannel 10`
- `/search <query>` - Web search with optional indexing
  - Example: `/search семейное право развод`

### AI Assistant

- `/ask <question>` - Ask question about active case
  - Example: `/ask Какие документы нужны для развода?`
- `/train` - Reindex/retrain active case data

### System & Admin

- `/status` - System health and statistics
- `/admin providers` - Manage LLM providers (admin only)
- `/admin limits` - View system limits (admin only)
- `/admin retrain` - Trigger full system reindexing (admin only)

## File Support

### Supported File Types

- **Documents**: PDF, DOCX, TXT, RTF
- **Images**: JPG, PNG, TIFF (with OCR)
- **Archives**: ZIP (extracts and processes contents)

### File Processing

1. **Upload**: Files are uploaded to S3 storage
2. **Text Extraction**: Content is extracted using appropriate parsers
3. **Chunking**: Text is split into searchable chunks
4. **Indexing**: Chunks are embedded and stored in Pinecone
5. **Retrieval**: Content becomes searchable via `/ask` command

## Security Features

- **Admin-only Commands**: Restricted by `TELEGRAM_ADMIN_USER_ID`
- **Rate Limiting**: 20 requests per minute per user
- **File Size Limits**: Configurable via `MAX_FILE_MB`
- **Domain Filtering**: Optional URL allowlist via `ALLOWED_DOMAINS`
- **Secret Redaction**: Sensitive data removed from logs
- **Input Validation**: All user inputs are validated and sanitized

## Logging

Structured JSON logging with correlation IDs:

```json
{
  "event": "telegram_event",
  "correlation_id": "abc12345",
  "user_id": 123456789,
  "chat_id": -987654321,
  "cmd": "ask",
  "latency_ms": 1250.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Architecture

The bot uses a clean adapter pattern to integrate with existing core services:

- **Handlers**: Process Telegram updates and commands
- **Adapters**: Thin layer connecting handlers to core services
- **Middlewares**: Cross-cutting concerns (logging, rate limiting, errors)
- **Core Services**: Existing business logic (RAG, LLM, storage, etc.)

## Health Monitoring

The bot performs periodic health checks and reports status:

- **Database**: PostgreSQL connectivity
- **Vector Store**: Pinecone availability
- **LLM Providers**: API endpoint status
- **Storage**: S3 bucket access
- **Queue Depth**: Pending processing tasks

Admin users receive notifications if system health degrades.

## Development

### Running Tests

```bash
pytest tests/smoke/ -v
```

### Adding New Commands

1. Add handler in `handlers.py`
2. Create adapter method if needed in `adapters.py`
3. Register handler in `register_handlers()`
4. Add tests in `tests/smoke/`

### Bot Token Setup

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command
3. Follow instructions to get your bot token
4. Set `TELEGRAM_BOT_TOKEN` in your `.env` file

## Production Deployment

For production deployment:

1. Use webhook instead of polling for better performance
2. Set up proper logging aggregation
3. Configure health monitoring and alerting
4. Use Redis for rate limiting and session storage
5. Set up backup and disaster recovery for S3 and database

## Troubleshooting

### Common Issues

1. **Bot doesn't respond**: Check `TELEGRAM_BOT_TOKEN` is correct
2. **File upload fails**: Verify S3 credentials and bucket permissions
3. **AI responses empty**: Check LLM provider API keys and quotas
4. **Search returns no results**: Ensure documents are indexed in Pinecone

### Debug Mode

Set `LOG_LEVEL=DEBUG` for verbose logging.