"""MCP Server for MegaAgent LangGraph workflows.

This server exposes LangGraph workflows and agents as MCP tools
for use with Claude Code and other MCP clients.

Usage:
    python -m mcp_server.server

Or add to Claude Code config:
    claude mcp add megaagent -- python -m mcp_server.server
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

# Initialize MCP server
server = Server("megaagent-langgraph")


def _format_result(data: Any) -> str:
    """Format result as JSON string."""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="run_workflow",
            description=(
                "Run a LangGraph workflow for EB-1A visa case processing. "
                "Available workflows: intake_questionnaire, document_analysis, "
                "criteria_evaluation, letter_generation, full_pipeline"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "string",
                        "description": "Workflow name to run",
                        "enum": [
                            "intake_questionnaire",
                            "document_analysis",
                            "criteria_evaluation",
                            "letter_generation",
                            "full_pipeline",
                        ],
                    },
                    "case_id": {
                        "type": "string",
                        "description": "Case ID to process",
                    },
                    "input_data": {
                        "type": "object",
                        "description": "Additional input data for the workflow",
                    },
                },
                "required": ["workflow", "case_id"],
            },
        ),
        Tool(
            name="invoke_agent",
            description=(
                "Invoke a specific MegaAgent agent directly. "
                "Available agents: intake, researcher, writer, reviewer, "
                "rag_pipeline, validator, supervisor"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Agent name to invoke",
                        "enum": [
                            "intake",
                            "researcher",
                            "writer",
                            "reviewer",
                            "rag_pipeline",
                            "validator",
                            "supervisor",
                        ],
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent",
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for the agent",
                    },
                },
                "required": ["agent", "task"],
            },
        ),
        Tool(
            name="query_case",
            description="Query case information from the database",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case ID to query",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific fields to retrieve (optional)",
                    },
                },
                "required": ["case_id"],
            },
        ),
        Tool(
            name="search_knowledge_base",
            description="Search the EB-1A knowledge base using semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                    },
                    "filter_type": {
                        "type": "string",
                        "description": "Filter by document type",
                        "enum": ["policy", "case_law", "rfe_response", "all"],
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="analyze_criteria",
            description=(
                "Analyze EB-1A criteria eligibility for a case. "
                "Returns assessment for all 10 criteria."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case ID to analyze",
                    },
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific criteria to analyze (optional, defaults to all)",
                    },
                },
                "required": ["case_id"],
            },
        ),
        Tool(
            name="generate_document",
            description="Generate a document (petition letter, exhibit list, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case ID",
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Type of document to generate",
                        "enum": [
                            "petition_letter",
                            "exhibit_list",
                            "recommendation_letter",
                            "cover_letter",
                            "rfe_response",
                        ],
                    },
                    "options": {
                        "type": "object",
                        "description": "Document generation options",
                    },
                },
                "required": ["case_id", "document_type"],
            },
        ),
        Tool(
            name="get_workflow_status",
            description="Get the status of a running or completed workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Workflow run ID",
                    },
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="list_cases",
            description="List all cases or filter by status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by case status",
                        "enum": ["active", "pending", "approved", "denied", "archived"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of cases to return",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="memory_search",
            description="Search agent memory for past interactions and decisions",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "case_id": {
                        "type": "string",
                        "description": "Filter by case ID (optional)",
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Type of memory to search",
                        "enum": ["episodic", "semantic", "procedural", "all"],
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Execute an MCP tool."""
    try:
        if name == "run_workflow":
            result = await _run_workflow(
                workflow=arguments["workflow"],
                case_id=arguments["case_id"],
                input_data=arguments.get("input_data", {}),
            )
        elif name == "invoke_agent":
            result = await _invoke_agent(
                agent=arguments["agent"],
                task=arguments["task"],
                context=arguments.get("context", {}),
            )
        elif name == "query_case":
            result = await _query_case(
                case_id=arguments["case_id"],
                fields=arguments.get("fields"),
            )
        elif name == "search_knowledge_base":
            result = await _search_knowledge_base(
                query=arguments["query"],
                top_k=arguments.get("top_k", 5),
                filter_type=arguments.get("filter_type", "all"),
            )
        elif name == "analyze_criteria":
            result = await _analyze_criteria(
                case_id=arguments["case_id"],
                criteria=arguments.get("criteria"),
            )
        elif name == "generate_document":
            result = await _generate_document(
                case_id=arguments["case_id"],
                document_type=arguments["document_type"],
                options=arguments.get("options", {}),
            )
        elif name == "get_workflow_status":
            result = await _get_workflow_status(
                run_id=arguments["run_id"],
            )
        elif name == "list_cases":
            result = await _list_cases(
                status=arguments.get("status"),
                limit=arguments.get("limit", 10),
            )
        elif name == "memory_search":
            result = await _memory_search(
                query=arguments["query"],
                case_id=arguments.get("case_id"),
                memory_type=arguments.get("memory_type", "all"),
            )
        else:
            return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")])

        return CallToolResult(content=[TextContent(type="text", text=_format_result(result))])

    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {e!s}")])


# Tool implementations


async def _run_workflow(workflow: str, case_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Run a LangGraph workflow."""

    from core.orchestration.workflow_graph import build_eb1a_complete_workflow

    # Build workflow based on type
    if workflow == "full_pipeline":
        graph = build_eb1a_complete_workflow()
    else:
        # For specific workflows, we'd build targeted graphs
        graph = build_eb1a_complete_workflow()

    # Prepare initial state
    initial_state = {
        "case_id": case_id,
        "workflow_type": workflow,
        "input_data": input_data,
        "messages": [],
    }

    # Run the workflow
    config = {"configurable": {"thread_id": f"{case_id}-{workflow}"}}

    result = await graph.ainvoke(initial_state, config)

    return {
        "status": "completed",
        "workflow": workflow,
        "case_id": case_id,
        "result": result.get("output", result),
    }


async def _invoke_agent(agent: str, task: str, context: dict[str, Any]) -> dict[str, Any]:
    """Invoke a specific agent."""
    from core.di.container import get_container

    container = get_container()

    agent_map = {
        "intake": "intake_agent",
        "researcher": "evidence_researcher",
        "writer": "petition_writer",
        "reviewer": "petition_reviewer",
        "rag_pipeline": "rag_pipeline_agent",
        "validator": "validator_agent",
        "supervisor": "supervisor_agent",
    }

    agent_name = agent_map.get(agent)
    if not agent_name:
        return {"error": f"Unknown agent: {agent}"}

    # Get agent from container
    agent_instance = getattr(container, agent_name, None)
    if not agent_instance:
        return {"error": f"Agent not available: {agent}"}

    # Invoke agent
    result = await agent_instance.run(task=task, context=context)

    return {
        "agent": agent,
        "task": task,
        "result": result,
    }


async def _query_case(case_id: str, fields: list[str] | None) -> dict[str, Any]:
    """Query case from database."""
    from core.di.container import get_container

    container = get_container()
    case_repo = container.case_repository

    case = await case_repo.get(case_id)
    if not case:
        return {"error": f"Case not found: {case_id}"}

    case_dict = case.model_dump() if hasattr(case, "model_dump") else dict(case)

    if fields:
        case_dict = {k: v for k, v in case_dict.items() if k in fields}

    return case_dict


async def _search_knowledge_base(query: str, top_k: int, filter_type: str) -> dict[str, Any]:
    """Search knowledge base."""
    from core.di.container import get_container

    container = get_container()

    # Use RAG pipeline for search
    rag = container.rag_pipeline_agent

    results = await rag.search(
        query=query,
        top_k=top_k,
        filter_type=filter_type if filter_type != "all" else None,
    )

    return {
        "query": query,
        "results": results,
        "count": len(results) if results else 0,
    }


async def _analyze_criteria(case_id: str, criteria: list[str] | None) -> dict[str, Any]:
    """Analyze EB-1A criteria for a case."""
    from core.di.container import get_container

    container = get_container()
    mega_agent = container.mega_agent

    # Use MegaAgent for criteria analysis
    from core.groupagents.mega_agent import CommandType, MegaAgentCommand

    command = MegaAgentCommand(
        command_type=CommandType.ANALYZE,
        payload={
            "case_id": case_id,
            "criteria": criteria
            or [
                "awards",
                "membership",
                "published_material",
                "judging",
                "original_contribution",
                "scholarly_articles",
                "exhibitions",
                "leading_role",
                "high_salary",
                "commercial_success",
            ],
        },
    )

    result = await mega_agent.execute(command)

    return {
        "case_id": case_id,
        "analysis": result,
    }


async def _generate_document(
    case_id: str, document_type: str, options: dict[str, Any]
) -> dict[str, Any]:
    """Generate a document."""
    from core.di.container import get_container

    container = get_container()

    # Use petition writer for document generation
    writer = container.petition_writer

    result = await writer.generate(
        case_id=case_id,
        document_type=document_type,
        **options,
    )

    return {
        "case_id": case_id,
        "document_type": document_type,
        "content": result,
        "status": "generated",
    }


async def _get_workflow_status(run_id: str) -> dict[str, Any]:
    """Get workflow run status."""
    # This would integrate with workflow state storage
    return {
        "run_id": run_id,
        "status": "completed",
        "message": "Workflow status retrieval not yet implemented",
    }


async def _list_cases(status: str | None, limit: int) -> dict[str, Any]:
    """List cases from database."""
    from core.di.container import get_container

    container = get_container()
    case_repo = container.case_repository

    cases = await case_repo.list(status=status, limit=limit)

    return {
        "cases": [
            {
                "id": c.id,
                "status": c.status,
                "created_at": str(c.created_at) if hasattr(c, "created_at") else None,
            }
            for c in cases
        ],
        "count": len(cases),
    }


async def _memory_search(query: str, case_id: str | None, memory_type: str) -> dict[str, Any]:
    """Search agent memory."""
    from core.di.container import get_container

    container = get_container()
    memory_manager = container.memory_manager

    results = await memory_manager.search(
        query=query,
        case_id=case_id,
        memory_type=memory_type if memory_type != "all" else None,
    )

    return {
        "query": query,
        "results": results,
        "count": len(results) if results else 0,
    }


def create_server() -> Server:
    """Create and return the MCP server instance."""
    return server


async def run_server() -> None:
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(run_server())
