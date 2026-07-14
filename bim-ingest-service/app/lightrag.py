from __future__ import annotations

from typing import Any

import httpx

from .models import TextChunk


class LightRagClient:
    def __init__(self, base_url: str, api_key: str, mode: str = "adapter"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.mode = mode

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def ingest_chunks(self, project_id: str, chunks: list[TextChunk]) -> dict[str, Any]:
        if not self.enabled or not chunks:
            return {"enabled": False, "inserted": 0}

        async with httpx.AsyncClient(timeout=60) as client:
            if self.mode == "adapter":
                payload = {
                    "conversationId": f"bim:{project_id}",
                    "channel": "bim",
                    "date": "bim",
                    "items": [{"role": "system", "content": c.text, "messageId": c.id} for c in chunks],
                }
                response = await client.post(
                    f"{self.base_url}/adapter/ingest",
                    headers=self.headers(),
                    json=payload,
                )
            else:
                payload = {
                    "text": "\n\n".join(c.text for c in chunks),
                    "metadata": {"project_id": project_id, "source": "bim-ingest-service"},
                }
                response = await client.post(
                    f"{self.base_url}/documents/text",
                    headers=self.headers(),
                    json=payload,
                )
            response.raise_for_status()
            return {"enabled": True, "inserted": len(chunks), "raw": response.json() if response.content else {}}

    async def query(self, project_id: str, question: str, top_k: int) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "contextItems": []}

        async with httpx.AsyncClient(timeout=60) as client:
            if self.mode == "adapter":
                response = await client.post(
                    f"{self.base_url}/adapter/query",
                    headers=self.headers(),
                    json={"query": question, "topK": top_k, "conversationId": f"bim:{project_id}"},
                )
            else:
                response = await client.post(
                    f"{self.base_url}/query",
                    headers=self.headers(),
                    json={"query": question, "top_k": top_k},
                )
            response.raise_for_status()
            return response.json()
