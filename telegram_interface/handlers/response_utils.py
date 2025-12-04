"""Response utilities for Telegram handlers.

Handles the logic of sending responses as text or file based on length.
"""

from __future__ import annotations

import io

import structlog
from telegram import Message

logger = structlog.get_logger(__name__)

# Telegram message limit
TELEGRAM_MAX_LENGTH = 4096


async def send_response(
    message: Message,
    text: str,
    filename: str = "response.txt",
    parse_mode: str | None = "Markdown",
    caption: str | None = None,
) -> None:
    """Send response as text message or file based on length.

    If text <= 4096 chars: sends as regular message
    If text > 4096 chars: sends as .txt file attachment

    Args:
        message: Telegram message to reply to
        text: Response text content
        filename: Filename for file attachment (default: response.txt)
        parse_mode: Parse mode for text message (default: Markdown)
        caption: Optional caption for file (shown above file)
    """
    if len(text) <= TELEGRAM_MAX_LENGTH:
        # Send as regular text message
        try:
            await message.reply_text(text, parse_mode=parse_mode)
            logger.info(
                "response.sent_as_text",
                length=len(text),
            )
        except Exception as e:
            # Fallback: try without parse_mode if Markdown fails
            logger.warning("response.markdown_failed", error=str(e))
            await message.reply_text(text, parse_mode=None)
    else:
        # Send as file attachment
        await send_as_file(
            message=message,
            text=text,
            filename=filename,
            caption=caption,
        )


async def send_as_file(
    message: Message,
    text: str,
    filename: str = "response.txt",
    caption: str | None = None,
) -> None:
    """Send text as a .txt file attachment.

    Args:
        message: Telegram message to reply to
        text: Text content for the file
        filename: Name of the file (default: response.txt)
        caption: Optional caption for the file
    """
    # Create in-memory file
    file_bytes = text.encode("utf-8")
    file_obj = io.BytesIO(file_bytes)
    file_obj.name = filename

    # Default caption if not provided
    if caption is None:
        caption = f"📄 Ответ ({len(text)} символов)"

    await message.reply_document(
        document=file_obj,
        filename=filename,
        caption=caption,
    )

    logger.info(
        "response.sent_as_file",
        filename=filename,
        length=len(text),
    )


async def send_document_response(
    message: Message,
    content: str,
    doc_title: str,
    doc_type: str = "document",
) -> None:
    """Send document content as text or file.

    For generated documents like letters, petitions, etc.

    Args:
        message: Telegram message to reply to
        content: Document content
        doc_title: Title of the document
        doc_type: Type of document for filename
    """
    # Sanitize title for filename
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in doc_title)
    safe_title = safe_title[:50].strip()  # Limit length
    filename = f"{doc_type}_{safe_title}.txt"

    if len(content) <= TELEGRAM_MAX_LENGTH:
        # Send as formatted message
        await message.reply_text(content, parse_mode="Markdown")
        logger.info(
            "document.sent_as_text",
            doc_title=doc_title,
            length=len(content),
        )
    else:
        # Send as file
        caption = f"📄 {doc_title}\n📊 Размер: {len(content)} символов"
        await send_as_file(
            message=message,
            text=content,
            filename=filename,
            caption=caption,
        )
        logger.info(
            "document.sent_as_file",
            doc_title=doc_title,
            filename=filename,
            length=len(content),
        )
