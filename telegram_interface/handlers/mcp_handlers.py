"""MCP (Model Context Protocol) handlers for Telegram bot.

Provides commands to interact with MCP servers:
- /mcp_status - Check MCP connection status
- /mcp_tools - List available MCP tools
- /mcp_query - Query using MCP tools with LangChain
"""

from __future__ import annotations

import os

import structlog
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from core.mcp import MCPClientManager, mcp_client_context

from .context import BotContext

load_dotenv(override=True)

logger = structlog.get_logger(__name__)

# Global MCP manager for persistent connection
_mcp_manager: MCPClientManager | None = None


def _bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    return context.application.bot_data["bot_context"]


def _is_authorized(bot_context: BotContext, update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    authorized = bot_context.is_authorized(user_id)
    if not authorized and update.effective_message:
        update.effective_message.reply_text("Access denied.")
    return authorized


async def _reply(update: Update, text: str) -> None:
    """Reply to a message, splitting long responses."""
    message = update.effective_message
    if message is None:
        return

    chunk_size = 3500
    for i in range(0, len(text), chunk_size):
        await message.reply_text(text[i : i + chunk_size])


async def _get_mcp_manager() -> MCPClientManager:
    """Get or create global MCP manager."""
    global _mcp_manager
    if _mcp_manager is None:
        from core.mcp import MCPClientManager

        _mcp_manager = MCPClientManager()
    return _mcp_manager


async def mcp_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check MCP servers connection status."""
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.mcp_status.received", user_id=user_id)

    if not _is_authorized(bot_context, update):
        return

    try:
        manager = await _get_mcp_manager()

        status_lines = ["**MCP Server Status**\n"]

        # Get config info
        from core.mcp.config import DEFAULT_MCP_CONFIG

        for server in DEFAULT_MCP_CONFIG.servers:
            emoji = "ON" if server.enabled else "OFF"
            status_lines.append(f"- {server.name}: {emoji}")
            if server.description:
                status_lines.append(f"  {server.description}")

        status_lines.append(f"\nConnected: {'Yes' if manager.is_connected else 'No'}")

        if manager.is_connected:
            status_lines.append(f"Tools loaded: {len(manager.tools)}")

        await _reply(update, "\n".join(status_lines))
        logger.info("telegram.mcp_status.sent", user_id=user_id)

    except Exception as exc:
        logger.exception("telegram.mcp_status.error", error=str(exc))
        await _reply(update, f"Error checking MCP status: {exc}")


async def mcp_connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Connect to MCP servers."""
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.mcp_connect.received", user_id=user_id)

    if not _is_authorized(bot_context, update):
        return

    await _reply(update, "Connecting to MCP servers...")

    try:
        manager = await _get_mcp_manager()

        if manager.is_connected:
            await _reply(update, f"Already connected. {len(manager.tools)} tools available.")
            return

        tools = await manager.connect()

        tool_names = [t.name for t in tools]
        response = f"Connected successfully!\n\nLoaded {len(tools)} tools:\n"
        response += "\n".join(f"- {name}" for name in tool_names[:20])

        if len(tool_names) > 20:
            response += f"\n...and {len(tool_names) - 20} more"

        await _reply(update, response)
        logger.info("telegram.mcp_connect.success", user_id=user_id, tools_count=len(tools))

    except Exception as exc:
        logger.exception("telegram.mcp_connect.error", error=str(exc))
        await _reply(update, f"Failed to connect: {exc}")


async def mcp_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available MCP tools."""
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.mcp_tools.received", user_id=user_id)

    if not _is_authorized(bot_context, update):
        return

    try:
        manager = await _get_mcp_manager()

        if not manager.is_connected:
            await _reply(update, "Not connected. Use /mcp_connect first.")
            return

        tools = manager.list_tools()

        if not tools:
            await _reply(update, "No tools available.")
            return

        response = f"**Available MCP Tools ({len(tools)})**\n\n"

        for tool in tools[:30]:
            name = tool["name"]
            desc = tool.get("description", "No description")
            # Truncate long descriptions
            if len(desc) > 100:
                desc = desc[:97] + "..."
            response += f"**{name}**\n{desc}\n\n"

        if len(tools) > 30:
            response += f"...and {len(tools) - 30} more tools"

        await _reply(update, response)
        logger.info("telegram.mcp_tools.sent", user_id=user_id, count=len(tools))

    except Exception as exc:
        logger.exception("telegram.mcp_tools.error", error=str(exc))
        await _reply(update, f"Error listing tools: {exc}")


async def mcp_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Query using MCP tools with LangChain agent.

    Usage: /mcp_query <your question>

    Examples:
    - /mcp_query List files in current directory
    - /mcp_query Show my GitHub repositories
    - /mcp_query Query users from Supabase database
    """
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.mcp_query.received", user_id=user_id)

    if not _is_authorized(bot_context, update):
        return

    if not context.args:
        await _reply(
            update,
            "Usage: /mcp_query <question>\n\n"
            "Examples:\n"
            "- /mcp_query List files in current directory\n"
            "- /mcp_query Show my GitHub repos\n"
            "- /mcp_query Query users table from database",
        )
        return

    query = " ".join(context.args)
    await _reply(update, f"Processing query: {query}\n\nConnecting to MCP...")

    try:
        # Use context manager for clean connection handling
        async with mcp_client_context() as manager:
            tools = manager.tools

            if not tools:
                await _reply(update, "No MCP tools available. Check server configuration.")
                return

            await _reply(update, f"Connected. {len(tools)} tools available. Running agent...")

            # Create LangChain agent with MCP tools
            from langgraph.prebuilt import create_react_agent

            model = ChatOpenAI(
                model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY"),
            )

            # Create ReAct agent with MCP tools
            agent = create_react_agent(model, tools)

            # Run the agent
            result = await agent.ainvoke(
                {
                    "messages": [
                        SystemMessage(
                            content=(
                                "You are a helpful assistant with access to MCP tools. "
                                "Use the tools to answer user questions. "
                                "Be concise in your responses."
                            )
                        ),
                        HumanMessage(content=query),
                    ]
                }
            )

            # Extract final response
            messages = result.get("messages", [])
            if messages:
                final_message = messages[-1]
                response = getattr(final_message, "content", str(final_message))
            else:
                response = "No response from agent."

            await _reply(update, f"**Result:**\n\n{response}")
            logger.info(
                "telegram.mcp_query.success",
                user_id=user_id,
                query_length=len(query),
                response_length=len(response),
            )

    except Exception as exc:
        logger.exception("telegram.mcp_query.error", error=str(exc))
        await _reply(update, f"Error executing query: {exc}")


async def mcp_disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disconnect from MCP servers."""
    user_id = update.effective_user.id if update.effective_user else None
    bot_context = _bot_context(context)
    logger.info("telegram.mcp_disconnect.received", user_id=user_id)

    if not _is_authorized(bot_context, update):
        return

    try:
        manager = await _get_mcp_manager()

        if not manager.is_connected:
            await _reply(update, "Not connected.")
            return

        await manager.disconnect()
        await _reply(update, "Disconnected from MCP servers.")
        logger.info("telegram.mcp_disconnect.success", user_id=user_id)

    except Exception as exc:
        logger.exception("telegram.mcp_disconnect.error", error=str(exc))
        await _reply(update, f"Error disconnecting: {exc}")


def get_handlers(bot_context: BotContext) -> list[CommandHandler]:
    """Expose Telegram command handlers for MCP operations."""
    return [
        CommandHandler("mcp_status", mcp_status),
        CommandHandler("mcp_connect", mcp_connect),
        CommandHandler("mcp_tools", mcp_tools),
        CommandHandler("mcp_query", mcp_query),
        CommandHandler("mcp_disconnect", mcp_disconnect),
    ]
