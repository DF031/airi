from __future__ import annotations

import re
from typing import Iterable, List

import jieba


WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[。！？；;!?])"
    r"|(?<=[：:])(?=\s*\d+[.、](?!\d))"
    r"|(?=\s*\d+[.、](?!\d))"
    r"|(?=\s*[（(][一二三四五六七八九十]+[）)])"
    r"|\.(?=\s)"
)
STOP_TERMS = {
    "什么",
    "哪些",
    "如何",
    "怎么",
    "多少",
    "哪个",
    "哪天",
    "哪里",
    "时候",
    "具体",
    "特定",
    "固定",
    "除了",
    "额外",
    "怎么办",
    "由谁来",
    "是否",
    "可以",
    "应该",
    "需要",
    "帮我",
    "告诉",
    "请问",
    "进行",
    "如果",
    "中的",
    "以及",
    "相关",
    "一个",
    "这个",
}


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.replace("\u3000", " ")).strip()


def tokenize(text: str) -> List[str]:
    terms = []
    seen = set()
    for token in jieba.lcut(normalize_text(text).lower()):
        token = token.strip()
        if len(token) < 2 or token in STOP_TERMS:
            continue
        if re.fullmatch(r"\W+", token):
            continue
        if token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


def split_sentences(text: str) -> List[str]:
    return [part.strip() for part in SENTENCE_SPLIT_RE.split(normalize_text(text)) if part.strip()]


def term_recall(query_terms: Iterable[str], text: str) -> float:
    terms = list(dict.fromkeys(query_terms))
    if not terms:
        return 0.0
    haystack = normalize_text(text).lower()
    compact = re.sub(r"\s+", "", haystack)
    hits = 0
    for term in terms:
        term = term.lower()
        if term in haystack or re.sub(r"\s+", "", term) in compact:
            hits += 1
    return hits / len(terms)


def best_sentences(question: str, text: str, limit: int = 3) -> List[str]:
    query_terms = tokenize(question)
    scored = []
    for idx, sentence in enumerate(split_sentences(text) or [normalize_text(text)]):
        score = term_recall(query_terms, sentence)
        scored.append((score, -idx, sentence))
    scored.sort(reverse=True)
    return [sentence for score, _, sentence in scored[:limit] if score > 0 or len(scored) <= limit]
