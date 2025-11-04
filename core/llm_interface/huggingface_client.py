from __future__ import annotations

from typing import Any


class HuggingFaceClient:
    def __init__(self, model: str = "distilbert-base-uncased", **kwargs: Any) -> None:
        self.model = model
        self.kwargs = kwargs

    async def acomplete(self, prompt: str, **params: Any) -> dict[str, Any]:
        return {"model": self.model, "prompt": prompt, "output": "", "provider": "huggingface"}
