import asyncio
import json
from typing import List

from openai import AsyncOpenAI

from backend.core.config import Settings
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument


class CorrectiveRetriever(BaseRetriever):
    def __init__(self, base_retriever: BaseRetriever, settings: Settings, client: AsyncOpenAI):
        self.base_retriever = base_retriever
        self.settings = settings
        self.client = client

    async def retrieve(self, query: str) -> List[RetrievedDocument]:
        first_pass = await self.base_retriever.retrieve(query)
        if not self.settings.enable_crag_judge:
            return first_pass

        if not first_pass:
            rewritten = await self._rewrite(query, "no documents")
            return await self.base_retriever.retrieve(rewritten)

        decision = await self._judge(query, first_pass)
        if decision.get("relevant", True):
            return first_pass

        rewritten = decision.get("rewritten_query") or await self._rewrite(
            query,
            decision.get("reason", "low relevance"),
        )
        second_pass = await self.base_retriever.retrieve(rewritten)
        return second_pass or first_pass

    async def _judge(self, query: str, docs: List[RetrievedDocument]) -> dict:
        context = "\n---\n".join(doc.content[:500] for doc in docs[:3])
        prompt = """
You are a lightweight retrieval evaluator for a campus RAG system.
Decide whether the retrieved context can answer the question.
Return only JSON: {"relevant": true/false, "rewritten_query": "...", "reason": "..."}.
If relevant is true, rewritten_query can be empty.
"""
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.settings.resolved_chat_model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Question:\n{query}\n\nContext:\n{context}"},
                    ],
                ),
                timeout=self.settings.llm_timeout_sec,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            print(f"[crag] judge skipped: {exc}")
            return {"relevant": True, "rewritten_query": "", "reason": "judge_failed"}

    async def _rewrite(self, query: str, reason: str) -> str:
        prompt = "Rewrite the Chinese campus policy question into a concise retrieval query. Return only the query."
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.settings.resolved_chat_model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Question: {query}\nProblem: {reason}"},
                    ],
                ),
                timeout=self.settings.llm_timeout_sec,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return query
