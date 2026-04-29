import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict, List

from openai import AsyncOpenAI

from backend.avatar.action_planner import ActionPlanner
from backend.core.config import Settings
from backend.core.schemas import ChatRequest
from backend.memory.long_term import LongTermMemory
from backend.memory.short_term import build_sliding_window_memory
from backend.rag.retrievers.base import BaseRetriever, RetrievedDocument


SENTENCE_PATTERN = re.compile(r"^(.+?[。！？；.!?;])")


def sse(event: str, data: Dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ChatService:
    def __init__(
        self,
        settings: Settings,
        client: AsyncOpenAI,
        retriever: BaseRetriever,
        memory: LongTermMemory,
        action_planner: ActionPlanner,
    ):
        self.settings = settings
        self.client = client
        self.retriever = retriever
        self.memory = memory
        self.action_planner = action_planner

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        try:
            yield sse("status", {"state": "memory", "text": "正在整理短期记忆和长期画像"})
            user_memories = self.memory.retrieve(request.user_id, request.user_message)
            yield sse("memory", {"items": user_memories})

            yield sse("status", {"state": "retrieving", "text": "正在检索校园知识库"})
            if self._retriever_is_cold():
                yield sse(
                    "status",
                    {"state": "index_loading", "text": "首次加载知识库索引，可能需要1到3分钟"},
                )
            try:
                retrieved_docs = await asyncio.wait_for(
                    self.retriever.retrieve(request.user_message),
                    timeout=self._retrieval_timeout_sec(),
                )
            except TimeoutError:
                print("[rag] retrieval timed out, continuing without retrieved context")
                yield sse(
                    "status",
                    {"state": "retrieval_timeout", "text": "知识库检索超时，正在先直接回答"},
                )
                retrieved_docs = []
            except Exception as exc:
                print(f"[rag] retrieval failed, continuing without retrieved context: {exc}")
                yield sse(
                    "status",
                    {"state": "retrieval_error", "text": "知识库检索失败，正在先直接回答"},
                )
                retrieved_docs = []
            source_items = [item for item in (self._source_item(doc) for doc in retrieved_docs) if item]
            yield sse("sources", {"items": source_items})
            yield sse("retrieval", self._retrieval_item(retrieved_docs, source_items))

            messages = self._build_messages(request, retrieved_docs, user_memories)

            yield sse("avatar", {"expression": "thinking", "motion": "idle", "style": "thinking"})
            try:
                response = None
                max_retries = max(0, self.settings.llm_rate_limit_retries)
                for attempt in range(max_retries + 1):
                    try:
                        response = await asyncio.wait_for(
                            self.client.chat.completions.create(
                                model=self.settings.resolved_chat_model,
                                messages=messages,
                                stream=True,
                            ),
                            timeout=self.settings.llm_timeout_sec,
                        )
                        if attempt > 0:
                            yield sse("llm", {"status": "recovered", "model": self.settings.resolved_chat_model})
                            yield sse(
                                "status",
                                {"state": "generating", "text": f"{self.settings.llm_display_name} 已恢复，正在生成回答"},
                            )
                        break
                    except Exception as exc:
                        if self._should_retry_llm_error(exc) and attempt < max_retries:
                            delay = self._rate_limit_delay(attempt)
                            yield sse(
                                "llm",
                                {
                                    "status": "rate_limited",
                                    "model": self.settings.resolved_chat_model,
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "retry_in_sec": round(delay, 1),
                                },
                            )
                            yield sse(
                                "status",
                                {
                                    "state": "rate_limited",
                                    "text": f"{self.settings.llm_display_name} 免费接口触发速率限制，{int(delay)} 秒后重试",
                                },
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise

                if response is None:
                    raise RuntimeError(f"{self.settings.llm_display_name} 暂时没有返回可用响应")
            except Exception as exc:
                fallback_answer = self._portable_v4_answer(request.user_message, retrieved_docs)
                if fallback_answer:
                    print(f"[llm] generation failed, using PortableRAGV4 fallback: {exc}")
                    yield sse(
                        "llm",
                        {
                            "status": "fallback",
                            "model": self.settings.resolved_chat_model,
                            "reason": self._friendly_llm_error(exc),
                        },
                    )
                    yield sse(
                        "status",
                        {"state": "llm_fallback", "text": "大模型生成暂不可用，正在使用v4证据答案"},
                    )
                    async for event in self._stream_plain_answer(fallback_answer):
                        yield event
                    return
                raise RuntimeError(self._friendly_llm_error(exc)) from exc

            sentence_buffer = ""
            full_answer = ""
            async for chunk in response:
                if not chunk.choices or chunk.choices[0].delta.content is None:
                    continue
                text = chunk.choices[0].delta.content
                full_answer += text
                sentence_buffer += text
                yield sse("token", {"text": text})

                while True:
                    match = SENTENCE_PATTERN.match(sentence_buffer.strip())
                    if not match:
                        break
                    sentence = match.group(1).strip()
                    action = await self.action_planner.plan(sentence)
                    yield sse("sentence", {"text": sentence, "action": action})
                    start = sentence_buffer.find(sentence)
                    sentence_buffer = sentence_buffer[start + len(sentence) :] if start >= 0 else ""

            if sentence_buffer.strip():
                sentence = sentence_buffer.strip()
                action = await self.action_planner.plan(sentence)
                yield sse("sentence", {"text": sentence, "action": action})

            yield sse("avatar", {"expression": "warm", "motion": "idle", "style": "idle"})
            yield sse("done", {"answer_length": len(full_answer)})
        except Exception as exc:
            yield sse("error", {"message": str(exc)})
            yield sse("done", {"answer_length": 0})

    def _build_messages(
        self,
        request: ChatRequest,
        retrieved_docs: List[RetrievedDocument],
        user_memories: List[Dict],
    ) -> List[Dict[str, str]]:
        context_docs = [
            doc
            for doc in retrieved_docs
            if doc.content.strip() and not doc.metadata.get("answer_hint_only")
        ]
        ranked_context_docs = self._rank_context_docs(request.user_message, context_docs)
        context = "\n\n".join(
            f"[来源: {doc.source or 'unknown'}]\n{self._clean_answer_text(doc.content)[:900]}"
            for doc in ranked_context_docs[:6]
        )
        memories = "\n".join(f"- {item['content']}" for item in user_memories) or "无"
        portable_v4_state = self._portable_v4_prompt(request.user_message, retrieved_docs)

        system_prompt = f"""
Digital human stage-control tags:
1. Start each answer with one control tag like <|ACT:{{"emotion":"happy"}}|>.
2. You may insert a new <|ACT:{{"emotion":"think"}}|> before a sentence if the emotion changes.
3. Valid emotions are: neutral, happy, sad, angry, think, surprised, awkward, question, curious.
4. Optional ACT fields are motion, cognitive, intent and intensity. Keep all field values in English.
5. Use <|DELAY:1|> only when a short pause is useful. These tags are hidden from users and are never spoken by TTS.
你是 AIRI，一个面向校园知识服务的具身数字人智能体。
你需要自然、简洁、可靠地回答用户问题。

行为要求：
1. 校园制度、流程、手册类问题必须优先依据知识库片段回答。
2. 如果知识库没有足够依据，要明确说明“不确定”或“当前资料中未找到”。
3. 可以自然利用长期记忆，但不要泄露内部存储结构。
4. 回答要适合被语音播报，句子不要过长。
5. 如果 v4 检索器结论为 answered，只能基于该结论和证据片段组织答案，不要补充证据外事实。
6. 如果 v4 检索器结论为 insufficient_evidence，要说明资料不足，不要猜测。
7. 最终回答只给用户需要的结论，通常控制在 1 到 3 句话，不要复述目录、页码列表或大段原文。

长期记忆：
{memories}

v4 检索器结论：
{portable_v4_state}

知识库片段：
{context}
"""

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(build_sliding_window_memory(request.chat_history, max_turns=3))
        messages.append({"role": "user", "content": request.user_message})
        return messages

    def _source_item(self, doc: RetrievedDocument) -> Dict[str, Any] | None:
        if doc.metadata.get("answer_hint_only"):
            return None
        return {
            "source": doc.source,
            "score": doc.score,
            "preview": doc.content[:180],
            "retriever": doc.metadata.get("retriever"),
            "unit_type": doc.metadata.get("unit_type"),
            "status": doc.metadata.get("portable_v4_status"),
            "confidence": doc.metadata.get("portable_v4_confidence"),
        }

    def _retrieval_item(
        self,
        retrieved_docs: List[RetrievedDocument],
        source_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        metadata = self._portable_v4_metadata(retrieved_docs)
        if metadata:
            return {
                "engine": "portable_rag_v4",
                "status": metadata.get("portable_v4_status"),
                "confidence": metadata.get("portable_v4_confidence"),
                "source_count": len(source_items),
                "citation_count": len(metadata.get("portable_v4_citations") or []),
                "answer_hint": metadata.get("portable_v4_answer"),
            }
        return {
            "engine": self.settings.rag_strategy,
            "status": "retrieved" if source_items else "empty",
            "confidence": None,
            "source_count": len(source_items),
            "citation_count": 0,
            "answer_hint": "",
        }

    def _portable_v4_metadata(self, retrieved_docs: List[RetrievedDocument]) -> Dict[str, Any]:
        for doc in retrieved_docs:
            metadata = doc.metadata
            if metadata.get("portable_v4_answer"):
                return metadata
        return {}

    def _portable_v4_answer(self, question: str, retrieved_docs: List[RetrievedDocument]) -> str:
        metadata = self._portable_v4_metadata(retrieved_docs)
        if metadata.get("portable_v4_status") == "insufficient_evidence":
            return str(metadata.get("portable_v4_answer") or "知识库证据不足，暂时不能给出确定答案。").strip()

        extracted = self._extractive_fallback_answer(question, retrieved_docs)
        if extracted:
            return extracted

        answer = self._clean_answer_text(str(metadata.get("portable_v4_answer") or ""))
        if len(answer) > 260:
            answer = answer[:260].rstrip("，、；;。 ") + "。"
        return answer

    def _portable_v4_prompt(self, question: str, retrieved_docs: List[RetrievedDocument]) -> str:
        metadata = self._portable_v4_metadata(retrieved_docs)
        if not metadata:
            return "无"
        confidence = metadata.get("portable_v4_confidence")
        citations = metadata.get("portable_v4_citations") or []
        citation_text = "；".join(
            str(item.get("source") or item.get("title") or "")
            for item in citations[:5]
            if isinstance(item, dict)
        )
        return "\n".join(
            item
            for item in [
                f"状态：{metadata.get('portable_v4_status')}",
                f"置信度：{confidence:.3f}" if isinstance(confidence, (float, int)) else "",
                f"结论：{self._portable_v4_answer(question, retrieved_docs)}",
                f"引用：{citation_text}" if citation_text else "",
            ]
            if item
        )

    async def _stream_plain_answer(self, answer: str) -> AsyncGenerator[str, None]:
        yield sse("token", {"text": answer})
        sentence_buffer = answer
        while sentence_buffer.strip():
            match = SENTENCE_PATTERN.match(sentence_buffer.strip())
            if match:
                sentence = match.group(1).strip()
                start = sentence_buffer.find(sentence)
                sentence_buffer = sentence_buffer[start + len(sentence) :] if start >= 0 else ""
            else:
                sentence = sentence_buffer.strip()
                sentence_buffer = ""
            if sentence:
                action = await self.action_planner.plan(sentence)
                yield sse("sentence", {"text": sentence, "action": action})
        yield sse("avatar", {"expression": "warm", "motion": "idle", "style": "idle"})
        yield sse("done", {"answer_length": len(answer)})

    def _rate_limit_delay(self, attempt: int) -> float:
        base = max(1.0, self.settings.llm_rate_limit_backoff_sec)
        max_delay = max(base, self.settings.llm_rate_limit_max_backoff_sec)
        return min(base * (attempt + 1), max_delay)

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return any(
            marker in text
            for marker in [
                "429",
                "1302",
                "rate limit",
                "rate_limit",
                "resource_exhausted",
                "quota",
                "速率限制",
            ]
        )

    def _should_retry_llm_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        if not self._is_rate_limit_error(exc):
            return False
        if any(marker in text for marker in ["limit: 0", "permission_denied", "denied access"]):
            return False
        return True

    def _friendly_llm_error(self, exc: Exception) -> str:
        text = str(exc)
        lowered = text.lower()
        if self._is_rate_limit_error(exc):
            return f"{self.settings.llm_display_name} 免费接口当前触发速率或配额限制，请稍等一会儿再试。"
        if "403" in lowered or "permission_denied" in lowered or "denied access" in lowered:
            return f"{self.settings.llm_display_name} 项目权限被拒绝，请检查该 API Key 所属项目是否开通 Gemini API 免费配额。"
        if "401" in lowered or "1001" in lowered or "authorization" in lowered:
            return f"{self.settings.llm_display_name} API 鉴权失败，请检查当前 LLM API Key 是否已配置。"
        if "1211" in lowered or "模型不存在" in text:
            return f"模型 {self.settings.resolved_chat_model} 不可用，请检查 CHAT_MODEL 配置。"
        if "timeout" in lowered or "timed out" in lowered:
            return f"{self.settings.llm_display_name} 响应超时，请稍后重试。"
        return f"{self.settings.llm_display_name} 生成暂时不可用，请稍后重试。"

    def _retriever_is_cold(self) -> bool:
        return bool(getattr(self.retriever, "is_loaded", True) is False)

    def _retrieval_timeout_sec(self) -> float:
        timeout = self.settings.retrieval_timeout_sec + 5.0
        if self.settings.use_portable_rag_v4 and self._retriever_is_cold():
            timeout = max(timeout, self.settings.portable_rag_init_timeout_sec)
        return timeout

    def _extractive_fallback_answer(self, question: str, retrieved_docs: List[RetrievedDocument]) -> str:
        terms = self._query_terms(question)
        if not terms:
            return ""

        candidates = []
        for doc_index, doc in enumerate(retrieved_docs):
            if doc.metadata.get("answer_hint_only") or not doc.content.strip():
                continue
            for sent_index, sentence in enumerate(self._candidate_sentences(doc.content)):
                score = self._sentence_score(sentence, terms)
                if score <= 0:
                    continue
                candidates.append((score, doc_index, sent_index, sentence))

        if not candidates:
            return ""

        candidates.sort(key=lambda item: (item[0], -item[1], -item[2]), reverse=True)
        selected = []
        seen = set()
        for _, _, _, sentence in candidates:
            key = re.sub(r"\s+", "", sentence)
            if not key or key in seen:
                continue
            if any(key in re.sub(r"\s+", "", item) or re.sub(r"\s+", "", item) in key for item in selected):
                continue
            seen.add(key)
            selected.append(sentence)
            if len(selected) >= 2:
                break

        if not selected:
            return ""
        answer = "根据知识库，" + "；".join(item.rstrip("。；; ") for item in selected) + "。"
        return self._clean_answer_text(answer)

    def _rank_context_docs(self, question: str, docs: List[RetrievedDocument]) -> List[RetrievedDocument]:
        terms = self._query_terms(question)
        if not terms:
            return docs
        return sorted(
            docs,
            key=lambda doc: (
                self._sentence_score(doc.content, terms),
                float(doc.score or 0.0),
            ),
            reverse=True,
        )

    def _query_terms(self, text: str) -> List[str]:
        try:
            from experiments.rag_reproduction.raglab.portable.text import tokenize

            terms = tokenize(text)
        except Exception:
            terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text.lower())
        return list(dict.fromkeys(term for term in terms if len(term.strip()) >= 2))

    def _candidate_sentences(self, text: str) -> List[str]:
        cleaned = self._clean_answer_text(text)
        parts = re.split(r"(?<=[。！？；;!?])", cleaned)
        candidates = []
        for part in parts:
            sentence = part.strip()
            if not sentence:
                continue
            if len(sentence) < 12 or len(sentence) > 260:
                continue
            if "...." in sentence or sentence.count(".") > 8:
                continue
            candidates.append(sentence)
        return candidates

    def _sentence_score(self, sentence: str, terms: List[str]) -> float:
        compact_sentence = re.sub(r"\s+", "", sentence.lower())
        if not compact_sentence:
            return 0.0
        score = 0.0
        for term in terms:
            compact_term = re.sub(r"\s+", "", term.lower())
            if compact_term and compact_term in compact_sentence:
                score += max(1.0, len(compact_term) / 2.0)
        if "...." in sentence:
            score *= 0.15
        if len(sentence) > 180:
            score *= 0.75
        return score

    def _clean_answer_text(self, text: str) -> str:
        cleaned = re.sub(r"\.{4,}", " ", str(text))
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", cleaned)
        return cleaned
