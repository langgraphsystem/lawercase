from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response


router = APIRouter()


@router.get("/openapi.yaml")
async def get_openapi_yaml() -> Response:
    path = Path("openapi/mega_agent_pro.openapi.yaml")
    if not path.exists():
        raise HTTPException(status_code=404, detail="OpenAPI spec not found")
    data = path.read_text(encoding="utf-8")
    return Response(content=data, media_type="application/yaml")

