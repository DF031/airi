import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from openai import AsyncOpenAI

from backend.core.config import Settings


class LongTermMemory:
    def __init__(self, settings: Settings, client: AsyncOpenAI):
        self.settings = settings
        self.client = client
        self.db_path: Path = settings.memory_db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.0,
                    emotion TEXT NOT NULL DEFAULT 'neutral',
                    novelty REAL NOT NULL DEFAULT 0.0,
                    source_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memory_items(user_id)")

    def retrieve(self, user_id: str, query: str, limit: int = 4) -> List[Dict[str, str]]:
        query_terms = [term for term in query.replace("，", " ").replace("。", " ").split() if term]
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT type, content, importance, emotion, novelty, created_at
                FROM memory_items
                WHERE user_id = ?
                ORDER BY importance DESC, updated_at DESC
                LIMIT 20
                """,
                (user_id,),
            ).fetchall()

        scored = []
        for row in rows:
            content = row[1]
            lexical_score = sum(1 for term in query_terms if term in content)
            score = lexical_score + float(row[2])
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)

        memories = []
        for _, row in scored[:limit]:
            memories.append(
                {
                    "type": row[0],
                    "content": row[1],
                    "importance": row[2],
                    "emotion": row[3],
                    "novelty": row[4],
                    "created_at": row[5],
                }
            )
        return memories

    async def remember_from_message(self, user_id: str, user_message: str) -> None:
        if not self.settings.enable_memory_extraction:
            return
        user_message = user_message.strip()
        if not user_message:
            return

        extracted = await self._extract_memory(user_message)
        if not extracted or extracted.get("should_remember") is not True:
            return
        if float(extracted.get("importance", 0.0)) < 0.6:
            return

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT id FROM memory_items WHERE user_id = ? AND content = ?",
                (user_id, extracted["content"]),
            ).fetchone()
            if exists:
                conn.execute(
                    """
                    UPDATE memory_items
                    SET importance = ?, emotion = ?, novelty = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        extracted.get("importance", 0.7),
                        extracted.get("emotion", "neutral"),
                        extracted.get("novelty", 0.5),
                        now,
                        exists[0],
                    ),
                )
                return
            conn.execute(
                """
                INSERT INTO memory_items
                (user_id, type, content, importance, emotion, novelty, source_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    extracted.get("type", "semantic"),
                    extracted["content"],
                    extracted.get("importance", 0.7),
                    extracted.get("emotion", "neutral"),
                    extracted.get("novelty", 0.5),
                    user_message,
                    now,
                    now,
                ),
            )

    async def _extract_memory(self, user_message: str) -> Dict | None:
        prompt = """
You are a selective long-term memory writer for a digital human assistant.
Extract only stable, reusable user information. Do not store one-off questions.
Return only JSON:
{
  "should_remember": true/false,
  "type": "identity|preference|task|emotion|semantic",
  "content": "short memory in Chinese",
  "importance": 0.0-1.0,
  "emotion": "neutral|happy|sad|anxious|angry",
  "novelty": 0.0-1.0
}
"""
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.settings.resolved_chat_model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_message},
                    ],
                ),
                timeout=self.settings.llm_timeout_sec,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            print(f"[memory] skipped extraction: {exc}")
            return None
