from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_agent, get_current_user, map_role
from core.groupagents.mega_agent import CommandType, MegaAgentCommand

router = APIRouter(prefix="/v1/case", tags=["case"])


@router.post("/{action}")
async def case_action(
    action: str, payload: dict, agent=Depends(get_agent), user=Depends(get_current_user)
):
    role = map_role(user)
    cmd = MegaAgentCommand(
        user_id=user.get("sub") or user.get("user_id") or "user",
        command_type=CommandType.CASE,
        action=action,
        payload=payload,
    )
    resp = await agent.handle_command(cmd, user_role=role)
    return resp.model_dump()
