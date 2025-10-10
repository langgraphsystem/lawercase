from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_agent, get_current_user, map_role
from api.schemas import AgentCommandRequest, AskRequest, SearchRequest, ToolRequest
from core.groupagents.mega_agent import CommandType, MegaAgentCommand

router = APIRouter(prefix="/v1", tags=["agent"])


@router.post("/agent/command")
async def agent_command(
    body: AgentCommandRequest, agent=Depends(get_agent), user=Depends(get_current_user)
):
    role = map_role(user)
    cmd = MegaAgentCommand(
        user_id=body.user_id,
        command_type=CommandType(body.command_type),
        action=body.action,
        payload=body.payload or {},
    )
    resp = await agent.handle_command(cmd, user_role=role)
    return resp.model_dump()


@router.post("/ask")
async def ask(body: AskRequest, agent=Depends(get_agent), user=Depends(get_current_user)):
    role = map_role(user)
    cmd = MegaAgentCommand(
        user_id=user.get("sub") or user.get("user_id") or "user",
        command_type=CommandType.ASK,
        action="ask",
        payload={"query": body.query},
    )
    resp = await agent.handle_command(cmd, user_role=role)
    return resp.model_dump()


@router.post("/search")
async def search(body: SearchRequest, agent=Depends(get_agent), user=Depends(get_current_user)):
    role = map_role(user)
    cmd = MegaAgentCommand(
        user_id=user.get("sub") or user.get("user_id") or "user",
        command_type=CommandType.SEARCH,
        action="search",
        payload=body.model_dump(),
    )
    resp = await agent.handle_command(cmd, user_role=role)
    return resp.model_dump()


@router.post("/tool")
async def call_tool(body: ToolRequest, agent=Depends(get_agent), user=Depends(get_current_user)):
    role = map_role(user)
    payload = body.model_dump()
    cmd = MegaAgentCommand(
        user_id=user.get("sub") or user.get("user_id") or "user",
        command_type=CommandType.TOOL,
        action="run",
        payload=payload,
    )
    resp = await agent.handle_command(cmd, user_role=role)
    return resp.model_dump()
