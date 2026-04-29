import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from backend.avatar.action_planner import ActionPlanner
from backend.avatar.tts import TTSService
from backend.core.config import ROOT_DIR, get_settings
from backend.core.schemas import ChatRequest, TTSRequest
from backend.memory.long_term import LongTermMemory
from backend.rag.retrievers.factory import build_retriever
from backend.services.chat_service import ChatService


settings = get_settings()
client = AsyncOpenAI(
    api_key=settings.resolved_chat_api_key,
    base_url=settings.resolved_chat_base_url,
    timeout=settings.llm_timeout_sec,
)

knowledge_index: Any | None = None
vector_store = None
if settings.use_portable_rag_v4:
    print(f"[rag] using PortableRAGV4 with campus corpus: {settings.knowledge_dir}")
else:
    from backend.rag.index_manager import KnowledgeIndex

    knowledge_index = KnowledgeIndex(settings)
    vector_store = knowledge_index.load_or_build()
retriever = build_retriever(knowledge_index, vector_store, settings, client)
memory = LongTermMemory(settings, client)
action_planner = ActionPlanner(settings, client)
chat_service = ChatService(settings, client, retriever, memory, action_planner)
tts_service = TTSService(settings)
FRONTEND_PUBLIC_DIR = ROOT_DIR / "frontend" / "public"
DEFAULT_AVATAR_MODEL_URL = "/live2d/hiyori/Hiyori.model3.json"

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-AIRI-Mouth-Cues", "X-AIRI-TTS-Engine"],
)


@app.on_event("startup")
async def warmup_retriever_on_startup():
    if not settings.use_portable_rag_v4 or not hasattr(retriever, "warmup"):
        return
    asyncio.create_task(warmup_retriever())


async def warmup_retriever():
    try:
        print("[rag] warming up PortableRAGV4 index in background")
        await retriever.warmup()
        print("[rag] PortableRAGV4 warmup complete")
    except Exception as exc:
        print(f"[rag] PortableRAGV4 warmup failed: {exc}")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "rag_strategy": settings.rag_strategy,
        "knowledge_dir": str(settings.knowledge_dir),
        "index_dir": (
            str(settings.portable_rag_config)
            if settings.use_portable_rag_v4 or knowledge_index is None
            else str(knowledge_index.loaded_index_dir or settings.active_index_dir)
        ),
        "portable_rag_config": str(settings.portable_rag_config) if settings.use_portable_rag_v4 else "",
    }


@app.get("/api/system/status")
async def system_status():
    return system_status_payload()


@app.get("/api/avatar/models")
async def avatar_models():
    return {
        "default_url": DEFAULT_AVATAR_MODEL_URL,
        "models": list_avatar_models(),
    }


@app.get("/api/tts/voices")
async def tts_voices():
    return {
        "engine": settings.tts_model,
        "selected": settings.tts_voice,
        "rate": settings.tts_rate,
        "voices": tts_service.available_voices(),
    }


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(memory.remember_from_message, request.user_id, request.user_message)
    return StreamingResponse(
        chat_service.stream_chat(request),
        media_type="text/event-stream",
    )


@app.post("/api/tts")
async def tts_endpoint(request: TTSRequest):
    try:
        audio = await tts_service.generate_audio(request.text, voice=request.voice, rate=request.rate)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    mouth_payload = json.dumps(
        {"engine": audio.engine, "cues": audio.mouth_cues},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    headers = {
        "X-AIRI-TTS-Engine": audio.engine,
        "X-AIRI-Mouth-Cues": base64.b64encode(mouth_payload.encode("utf-8")).decode("ascii"),
    }
    return Response(content=audio.data, media_type=audio.media_type, headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host=settings.host, port=settings.port, reload=False)


def system_status_payload() -> dict[str, Any]:
    rag_status = {
        "strategy": settings.rag_strategy,
        "knowledge_dir": str(settings.knowledge_dir),
        "corpus": summarize_dir(settings.knowledge_dir),
        "retriever": retriever.describe() if hasattr(retriever, "describe") else {"engine": settings.rag_strategy},
    }
    if settings.use_portable_rag_v4:
        portable_config = load_portable_status()
        rag_status.update(portable_config)
    elif knowledge_index is not None:
        rag_status["index_dir"] = str(knowledge_index.loaded_index_dir or settings.active_index_dir)

    return {
        "status": "ok",
        "app_name": settings.app_name,
        "host": settings.host,
        "port": settings.port,
        "chat_provider": settings.normalized_chat_provider,
        "chat_model": settings.resolved_chat_model,
        "llm_base_url": settings.resolved_chat_base_url,
        "rag": rag_status,
        "tts": {
            "engine": settings.tts_model,
            "voice": settings.tts_voice,
            "rate": settings.tts_rate,
            "cache_dir": str(settings.tts_cache_dir),
            "api_key_required": False,
            "voices": tts_service.available_voices(),
        },
        "memory": {
            "long_term_enabled": settings.enable_memory_extraction,
            "db_path": str(settings.memory_db_path),
            "db_exists": resolve_workspace_path(settings.memory_db_path).exists(),
        },
        "avatar": {
            "llm_actions_enabled": settings.enable_llm_actions,
            "action_planner": "rule_first",
        },
    }


def load_portable_status() -> dict[str, Any]:
    try:
        from experiments.rag_reproduction.raglab.portable.config import load_portable_config

        config = load_portable_config(settings.portable_rag_config)
        return {
            "portable_config": str(config.path),
            "portable_top_k": settings.portable_rag_top_k,
            "index_dir": str(config.index_dir),
            "index_cache": summarize_dir(config.index_dir),
        }
    except Exception as exc:
        return {
            "portable_config": str(settings.portable_rag_config),
            "portable_top_k": settings.portable_rag_top_k,
            "index_dir": "",
            "index_error": str(exc),
        }


def summarize_dir(path: Any) -> dict[str, Any]:
    resolved = resolve_workspace_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(path), "file_count": 0, "size_mb": 0.0}
    files = [item for item in resolved.rglob("*") if item.is_file()]
    size = sum(item.stat().st_size for item in files)
    return {
        "exists": True,
        "path": str(resolved),
        "file_count": len(files),
        "size_mb": round(size / 1024 / 1024, 2),
    }


def list_avatar_models() -> list[dict[str, Any]]:
    if not FRONTEND_PUBLIC_DIR.exists():
        return []

    models = []
    for model_path in sorted(FRONTEND_PUBLIC_DIR.rglob("*.model3.json")):
        try:
            rel_path = model_path.relative_to(FRONTEND_PUBLIC_DIR).as_posix()
            data = json.loads(model_path.read_text(encoding="utf-8"))
            file_refs = data.get("FileReferences") or {}
            groups = data.get("Groups") or []
            lip_sync_params = [
                param
                for group in groups
                if group.get("Name") == "LipSync"
                for param in group.get("Ids", [])
            ]
            expressions = [item.get("Name") for item in file_refs.get("Expressions", []) if item.get("Name")]
            motions = file_refs.get("Motions") or {}
            models.append(
                {
                    "id": model_id_from_path(model_path),
                    "name": model_display_name(model_path),
                    "url": f"/{rel_path}",
                    "path": rel_path,
                    "lip_sync_params": lip_sync_params,
                    "expressions": expressions,
                    "motion_groups": {str(name): len(items) for name, items in motions.items()},
                    "motion_group_labels": {str(name): (name or "default") for name in motions},
                }
            )
        except Exception as exc:
            print(f"[avatar] skipped model {model_path}: {exc}")
    return models


def model_id_from_path(path: Path) -> str:
    return path.name.replace(".model3.json", "").lower().replace("_", "-")


def model_display_name(path: Path) -> str:
    stem = path.name.replace(".model3.json", "")
    if path.parent.name.lower() == "runtime":
        folder = path.parent.parent.name
        if stem.lower().startswith(folder.lower()) or stem.lower() in {"model", "avatar"}:
            stem = folder
    return stem.replace("_", " ").replace("-", " ").strip().title()


def resolve_workspace_path(path: Any):
    value = path if hasattr(path, "is_absolute") else ROOT_DIR / str(path)
    return value if value.is_absolute() else ROOT_DIR / value
