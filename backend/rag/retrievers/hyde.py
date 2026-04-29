import asyncio
from typing import List

from openai import AsyncOpenAI

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument


class HyDERetriever(BaseRetriever):
    def __init__(self, base_retriever: BaseRetriever, settings: Settings, client: AsyncOpenAI):
        self.base_retriever = base_retriever
        self.settings = settings
        self.client = client

    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        if not self.settings.enable_hyde:
            return await self.base_retriever.retrieve(query)
        hyde_query = await self._make_hypothetical_document(query)
        return await self.base_retriever.retrieve(hyde_query or query)

    async def _make_hypothetical_document(self, query: str) -> str:
        prompt = (
            "Generate a concise hypothetical Chinese reference passage that would answer "
            "the user's campus policy question. Do not fabricate exact numbers unless the "
            "question includes them. Return only the passage."
        )
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.settings.resolved_chat_model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": query},
                    ],
                ),
                timeout=self.settings.llm_timeout_sec,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"[hyde] fallback to raw query: {exc}")
            return query
