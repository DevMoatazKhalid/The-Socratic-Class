"""
NVIDIA Multilingual Embedding Provider.

Connects to NVIDIA NIM (e.g. https://integrate.api.nvidia.com/v1) for high-performance
multilingual retrieval embeddings. Correctly supplies `input_type="passage"` for document
indexing and `input_type="query"` for search queries.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from ai.rag.config import get_rag_config

logger = logging.getLogger(__name__)


class NVIDIAEmbeddingProvider:
    """NVIDIA NIM embedding provider (default model: nvidia/nv-embedqa-e5-v5, 1024-dim)."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None,
        timeout: float = 45.0,
        max_retries: int = 2,
    ) -> None:
        cfg = get_rag_config()
        self.model = model or cfg.embedding_model
        self.api_key = api_key or cfg.embedding_api_key
        raw_base = base_url or cfg.embedding_base_url or "https://integrate.api.nvidia.com/v1"
        self.base_url = raw_base.rstrip("/")
        self._dim = dimension or cfg.embedding_dim
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = 48

    @property
    def dimension(self) -> int:
        return self._dim

    def _call_api(self, inputs: list[str], input_type: str) -> list[list[float]]:
        if not self.api_key:
            raise ValueError(
                "NVIDIA API key not set. Provide RAG_EMBEDDING_API_KEY, NVIDIA_API_KEY, or AI_API_KEY in .env."
            )

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "input": inputs,
            "input_type": input_type,
        }

        with httpx.Client(timeout=self.timeout) as client:
            last_err: Optional[Exception] = None
            for attempt in range(self.max_retries + 1):
                try:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                    # Sort embeddings by item index
                    items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
                    embeddings = [item["embedding"] for item in items]
                    return embeddings
                except Exception as exc:
                    last_err = exc
                    logger.warning(
                        "NVIDIA embedding call attempt %d failed: %s", attempt + 1, exc
                    )
            raise RuntimeError(
                f"Failed to generate NVIDIA embeddings after {self.max_retries + 1} attempts: {last_err}"
            ) from last_err

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Compute passage embeddings for documents in batches."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            # Replace empty strings with a single space to avoid API validation errors
            clean_batch = [t if t.strip() else " " for t in batch]
            embeddings = self._call_api(clean_batch, input_type="passage")
            all_embeddings.extend(embeddings)

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Compute query embedding for search query."""
        clean_query = query.strip() or "course query"
        embeddings = self._call_api([clean_query], input_type="query")
        return embeddings[0]
