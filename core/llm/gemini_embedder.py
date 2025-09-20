from __future__ import annotations


class GeminiEmbedder:
    """Embeddings adapter for Gemini "gemini-embedding-001" only.

    - Uses google-generativeai's embed_content.
    - Batch-first, then per-text fallback.
    - Dimensionality defaults to 3072.
    - Callers must guard with a feature flag and provide API key.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-embedding-001",
        output_dimensionality: int | None = 3072,
        truncate_chars: int = 2000,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.output_dimensionality = output_dimensionality
        self.truncate_chars = truncate_chars

        # Common embedding dimensions for reference; not strictly enforced
        if model == "gemini-embedding-001" or model.endswith("gemini-embedding-001"):
            self.embedding_dim = 3072
        else:
            # Unsupported model; enforce integration constraint
            self.embedding_dim = 0

    async def aembed(self, texts: list[str]) -> list[list[float]]:
        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            # Library not installed or import error; return empty vectors
            return [[] for _ in texts]

        if not self.api_key or not self.model:
            return [[] for _ in texts]

        # Enforce supported model
        model = "gemini-embedding-001"
        genai.configure(api_key=self.api_key)
        api_model = f"models/{model}"
        truncated = [t[: self.truncate_chars] for t in texts]

        # Attempt batch embedding first
        try:
            kwargs = {
                "model": api_model,
                "content": truncated,
                "task_type": "RETRIEVAL_DOCUMENT",
            }
            if self.output_dimensionality:
                kwargs["output_dimensionality"] = int(self.output_dimensionality)
            result = genai.embed_content(**kwargs)

            out: list[list[float]] = []
            if isinstance(result, dict):
                embeddings = result.get("embeddings", result.get("embedding", []))
                if isinstance(embeddings, list):
                    for emb in embeddings:
                        if isinstance(emb, dict) and "values" in emb:
                            out.append([float(x) for x in emb["values"]])
                        elif isinstance(emb, list):
                            out.append([float(x) for x in emb])
                        else:
                            out.append([])
                else:
                    out = [[] for _ in texts]
            elif hasattr(result, "embedding") and hasattr(result.embedding, "values"):
                # Single embedding returned; duplicate for all texts
                values = [float(x) for x in result.embedding.values]
                out = [values for _ in texts]
            else:
                out = [[] for _ in texts]

            if not self.embedding_dim and out and out[0]:
                self.embedding_dim = len(out[0])
            # Ensure length alignment
            if len(out) < len(texts):
                out.extend([[]] * (len(texts) - len(out)))
            return out[: len(texts)]
        except Exception:
            # Fallback to per-text requests
            pass

        out: list[list[float]] = []
        for t in truncated:
            try:
                kwargs = {
                    "model": api_model,
                    "content": t,
                    "task_type": "RETRIEVAL_DOCUMENT",
                }
                if self.output_dimensionality:
                    kwargs["output_dimensionality"] = int(self.output_dimensionality)
                result = genai.embed_content(**kwargs)
                if isinstance(result, dict) and "embedding" in result:
                    emb = result["embedding"]
                    if isinstance(emb, dict) and "values" in emb:
                        out.append([float(x) for x in emb["values"]])
                    elif isinstance(emb, list):
                        out.append([float(x) for x in emb])
                    else:
                        out.append([])
                elif hasattr(result, "embedding") and hasattr(result.embedding, "values"):
                    out.append([float(x) for x in result.embedding.values])
                else:
                    out.append([])
            except Exception:
                out.append([])

        if not self.embedding_dim and out and out[0]:
            self.embedding_dim = len(out[0])
        return out
