import asyncio
import hashlib
import json
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import edge_tts

from backend.core.config import Settings

try:
    from pypinyin import Style, lazy_pinyin
except Exception:  # pragma: no cover - optional local enhancement
    Style = None
    lazy_pinyin = None


@dataclass(frozen=True)
class GeneratedAudio:
    data: bytes
    media_type: str
    mouth_cues: list[dict]
    engine: str


EDGE_TTS_VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "locale": "zh-CN", "gender": "Female", "style": "清亮自然"},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓伊", "locale": "zh-CN", "gender": "Female", "style": "温柔"},
    {"id": "zh-CN-XiaohanNeural", "name": "晓涵", "locale": "zh-CN", "gender": "Female", "style": "亲和"},
    {"id": "zh-CN-XiaomengNeural", "name": "晓梦", "locale": "zh-CN", "gender": "Female", "style": "活泼"},
    {"id": "zh-CN-XiaomoNeural", "name": "晓墨", "locale": "zh-CN", "gender": "Female", "style": "稳重"},
    {"id": "zh-CN-XiaoqiuNeural", "name": "晓秋", "locale": "zh-CN", "gender": "Female", "style": "清晰"},
    {"id": "zh-CN-XiaorouNeural", "name": "晓柔", "locale": "zh-CN", "gender": "Female", "style": "柔和"},
    {"id": "zh-CN-XiaoruiNeural", "name": "晓睿", "locale": "zh-CN", "gender": "Female", "style": "正式"},
    {"id": "zh-CN-XiaoshuangNeural", "name": "晓双", "locale": "zh-CN", "gender": "Female", "style": "轻快"},
    {"id": "zh-CN-XiaoxuanNeural", "name": "晓萱", "locale": "zh-CN", "gender": "Female", "style": "明快"},
    {"id": "zh-CN-XiaoyanNeural", "name": "晓颜", "locale": "zh-CN", "gender": "Female", "style": "播报"},
    {"id": "zh-CN-XiaoyouNeural", "name": "晓悠", "locale": "zh-CN", "gender": "Female", "style": "儿童"},
    {"id": "zh-CN-YunxiNeural", "name": "云希", "locale": "zh-CN", "gender": "Male", "style": "年轻自然"},
    {"id": "zh-CN-YunjianNeural", "name": "云健", "locale": "zh-CN", "gender": "Male", "style": "有力"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬", "locale": "zh-CN", "gender": "Male", "style": "播音"},
    {"id": "zh-CN-YunfengNeural", "name": "云枫", "locale": "zh-CN", "gender": "Male", "style": "沉稳"},
    {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "辽宁晓北", "locale": "zh-CN", "gender": "Female", "style": "方言"},
    {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "陕西晓妮", "locale": "zh-CN", "gender": "Female", "style": "方言"},
]


PUNCTUATION_RE = re.compile(r"^[，,。！？!?；;、：:\s]+$")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"^[a-zA-Z]+$")

FALLBACK_VISEME_GROUPS = {
    "open": set("啊阿呀哑押压雅亚夏下家加假夹价查差茶答达大法发罚把爸吧马妈嘛哪拿那卡哈它他她啦拉撒杂咋"),
    "wide": set("一以已意衣医依义议易异益亿你里理力利立即及级机记技其期起气题体提第地递师时实是事知职制日资自字此次西系息习细齐七"),
    "tightRound": set("不部布步出处初除书数术输属主住注朱助入如乳需许须区去取曲局举具女旅律绿语雨鱼育于与玉遇"),
    "spread": set("的得德了乐这着者热认任人们门分本很和合河额饿学觉决月越约业也页叶给类美每北被内"),
    "round": set("我哦喔窝握过国果或活说做作错所多托脱罗落播坡破摸没某口后候周州收手"),
    "closed": set("吗嘛妈么没们明名民面免办报本不部被把爸吧播坡破评批票篇品"),
}

DIGIT_READINGS = {
    "0": "ling",
    "1": "yi",
    "2": "er",
    "3": "san",
    "4": "si",
    "5": "wu",
    "6": "liu",
    "7": "qi",
    "8": "ba",
    "9": "jiu",
}


class TTSService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_audio(self, text: str, voice: str | None = None, rate: str | None = None) -> GeneratedAudio:
        cleaned = text.strip()
        if not cleaned:
            return GeneratedAudio(b"", "audio/wav", [], "empty")

        selected_voice = self._voice_or_default(voice)
        selected_rate = self._rate_or_default(rate)
        engine = self.settings.tts_model.lower().strip()
        if engine in {"windows-sapi", "sapi", "system-speech"}:
            return await self._generate_windows_sapi(cleaned, selected_voice, selected_rate)

        try:
            return await self._generate_edge_tts(cleaned, selected_voice, selected_rate)
        except Exception as exc:
            print(f"[TTS] edge-tts failed, falling back to Windows SAPI: {exc}")
            return await self._generate_windows_sapi(cleaned, selected_voice, selected_rate)

    def available_voices(self) -> list[dict]:
        return EDGE_TTS_VOICES

    def _voice_or_default(self, voice: str | None) -> str:
        selected = (voice or self.settings.tts_voice).strip()
        if not selected:
            return self.settings.tts_voice
        return selected

    def _rate_or_default(self, rate: str | None) -> str:
        selected = (rate or self.settings.tts_rate).strip()
        return selected or self.settings.tts_rate

    async def _generate_edge_tts(self, text: str, voice: str, rate: str) -> GeneratedAudio:
        cache_path = self._cache_path("edge", text, "mp3", voice, rate)
        cue_cache_path = cache_path.with_suffix(".mouth.json")
        cached = self._read_cache(cache_path)
        if cached is not None:
            return GeneratedAudio(cached, "audio/mpeg", self._read_cues(cue_cache_path, text), "edge-tts")

        start_time = time.time()
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume="+0%",
        )
        chunks = []
        boundaries = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
            elif chunk["type"] in {"WordBoundary", "SentenceBoundary"}:
                boundaries.append(chunk)
        audio_data = b"".join(chunks)
        if not audio_data:
            raise RuntimeError("edge-tts returned empty audio")
        mouth_cues = self._build_mouth_cues(text, boundaries)
        self._write_cache(cache_path, audio_data)
        self._write_json(cue_cache_path, mouth_cues)
        print(f"[TTS] edge-tts generated {len(audio_data) / 1024:.1f} KB in {time.time() - start_time:.2f}s")
        return GeneratedAudio(audio_data, "audio/mpeg", mouth_cues, "edge-tts")

    async def _generate_windows_sapi(self, text: str, voice: str, rate: str) -> GeneratedAudio:
        cache_path = self._cache_path("sapi", text, "wav", voice, rate)
        cue_cache_path = cache_path.with_suffix(".mouth.json")
        cached = self._read_cache(cache_path)
        if cached is not None:
            return GeneratedAudio(cached, "audio/wav", self._read_cues(cue_cache_path, text), "windows-sapi")

        start_time = time.time()
        audio_data = await asyncio.to_thread(self._sapi_to_wav, text, voice, rate)
        if not audio_data:
            raise RuntimeError("Windows SAPI returned empty audio")
        duration = self._wav_duration(audio_data)
        mouth_cues = self._build_heuristic_cues(text, duration)
        self._write_cache(cache_path, audio_data)
        self._write_json(cue_cache_path, mouth_cues)
        print(f"[TTS] Windows SAPI generated {len(audio_data) / 1024:.1f} KB in {time.time() - start_time:.2f}s")
        return GeneratedAudio(audio_data, "audio/wav", mouth_cues, "windows-sapi")

    def _sapi_to_wav(self, text: str, selected_voice: str, selected_rate: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="airi_tts_") as temp_dir:
            temp_path = Path(temp_dir)
            script_path = temp_path / "speak.ps1"
            text_path = temp_path / "speech.txt"
            wav_path = temp_path / "speech.wav"
            text_path.write_text(text, encoding="utf-8")
            script_path.write_text(
                """
param(
  [string]$TextPath,
  [string]$OutputPath,
  [string]$VoiceName,
  [int]$Rate
)
Add-Type -AssemblyName System.Speech
$Text = [System.IO.File]::ReadAllText($TextPath, [System.Text.Encoding]::UTF8)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($VoiceName) {
    $synth.SelectVoice($VoiceName)
  }
} catch {
}
$synth.Rate = $Rate
$synth.SetOutputToWaveFile($OutputPath)
$synth.Speak($Text)
            $synth.Dispose()
""".strip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    "-TextPath",
                    str(text_path),
                    "-OutputPath",
                    str(wav_path),
                    "-VoiceName",
                    self._sapi_voice_name(selected_voice),
                    "-Rate",
                    str(self._sapi_rate(selected_rate)),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "Windows SAPI failed").strip())
            audio_data = wav_path.read_bytes()
            if len(audio_data) < 1024:
                raise RuntimeError("Windows SAPI returned empty audio")
            return audio_data

    def _sapi_voice_name(self, voice: str) -> str:
        if "Neural" in voice or "Xiaoxiao" in voice:
            return "Microsoft Huihui Desktop"
        return voice or "Microsoft Huihui Desktop"

    @staticmethod
    def _sapi_rate(rate: str) -> int:
        raw = rate.strip().replace("%", "")
        try:
            percent = int(raw)
        except ValueError:
            return 1
        return max(-10, min(10, round(percent / 6)))

    def _cache_path(self, engine: str, text: str, suffix: str, voice: str, rate: str) -> Path:
        key = "|".join([engine, voice, rate, text])
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.settings.tts_cache_dir / f"{digest}.{suffix}"

    def _build_mouth_cues(self, text: str, boundaries: list[dict]) -> list[dict]:
        usable_boundaries = [
            item for item in boundaries
            if self._boundary_duration(item) > 0 and self._boundary_text(item)
        ]
        if not usable_boundaries:
            return self._build_heuristic_cues(text)

        cues: list[dict] = []
        for boundary in usable_boundaries:
            start = self._boundary_offset(boundary)
            duration = self._boundary_duration(boundary)
            boundary_text = self._boundary_text(boundary)
            tokens = self._mouth_tokens(boundary_text)
            if not tokens:
                continue
            token_duration = max(0.045, duration / len(tokens))
            for index, token in enumerate(tokens):
                token_start = start + index * token_duration
                token_end = min(start + duration, token_start + token_duration)
                cues.append(self._cue(token_start, token_end, token))
        normalized = self._normalize_cues(cues)
        source_tokens = self._mouth_tokens(text)
        if len(normalized) < max(3, int(len(source_tokens) * 0.35)):
            start = min(self._boundary_offset(item) for item in usable_boundaries)
            end = max(self._boundary_offset(item) + self._boundary_duration(item) for item in usable_boundaries)
            return self._build_heuristic_cues(text, max(0.45, end - start), start=start)
        return normalized or self._build_heuristic_cues(text)

    def _build_heuristic_cues(self, text: str, duration: float | None = None, start: float = 0.06) -> list[dict]:
        tokens = self._mouth_tokens(text)
        if not tokens:
            return []
        total_duration = duration or max(0.75, len(tokens) * 0.145)
        token_duration = total_duration / len(tokens)
        cues = [
            self._cue(start + index * token_duration, start + (index + 1) * token_duration, token)
            for index, token in enumerate(tokens)
        ]
        return self._normalize_cues(cues)

    def _mouth_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        for item in re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]|[0-9]+|[，,。！？!?；;、]", text):
            if item.strip():
                tokens.append(item)
        return tokens

    def _cue(self, start: float, end: float, text: str) -> dict:
        cue = {
            "s": round(max(0.0, start), 3),
            "e": round(max(start + 0.035, end), 3),
            "t": text,
            "v": self._viseme_for_text(text),
        }
        onset = self._onset_viseme_for_text(text)
        if onset:
            cue["c"] = onset
        return cue

    def _normalize_cues(self, cues: list[dict]) -> list[dict]:
        normalized = sorted(cues, key=lambda item: item["s"])
        if not normalized:
            return []
        for cue in normalized:
            cue_text = str(cue.get("t") or "")
            cue["v"] = self._viseme_for_text(cue_text)
            onset = self._onset_viseme_for_text(cue_text)
            if onset:
                cue["c"] = onset
            else:
                cue.pop("c", None)
        for index in range(1, len(normalized)):
            previous = normalized[index - 1]
            current = normalized[index]
            if current["s"] < previous["e"]:
                current["s"] = round(previous["e"], 3)
            if current["e"] <= current["s"]:
                current["e"] = round(current["s"] + 0.045, 3)
        return normalized

    def _viseme_for_text(self, text: str) -> str:
        token = text.strip()
        if not token or PUNCTUATION_RE.match(token):
            return "rest"

        readings = self._phonetic_readings(token)
        if readings:
            visemes = [self._vowel_viseme_from_reading(reading) for reading in readings if reading]
            visemes = [item for item in visemes if item and item != "rest"]
            if visemes:
                return max(set(visemes), key=visemes.count)

        for viseme, chars in FALLBACK_VISEME_GROUPS.items():
            if viseme == "closed":
                continue
            if any(char in chars for char in token):
                return viseme

        return "open" if CHINESE_RE.search(token) else "spread"

    def _onset_viseme_for_text(self, text: str) -> str:
        token = text.strip()
        if not token or PUNCTUATION_RE.match(token):
            return ""

        readings = self._phonetic_readings(token)
        for reading in readings:
            onset = self._consonant_viseme_from_reading(reading)
            if onset:
                return onset

        if any(char in FALLBACK_VISEME_GROUPS["closed"] for char in token):
            return "closed"
        return ""

    def _phonetic_readings(self, token: str) -> list[str]:
        if LATIN_RE.match(token):
            return [token.lower()]
        if token.isdigit():
            return [DIGIT_READINGS.get(char, "") for char in token]
        if lazy_pinyin is not None and CHINESE_RE.search(token):
            try:
                return [
                    item.lower()
                    for item in lazy_pinyin(token, style=Style.NORMAL, errors="ignore")
                    if item
                ]
            except Exception:
                return []
        return []

    @staticmethod
    def _vowel_viseme_from_reading(reading: str) -> str:
        item = reading.lower().replace("ü", "v")
        if not item:
            return "rest"
        if item.endswith(("a", "ai", "an", "ang", "ao", "iao", "ua", "uai", "uan", "uang")):
            return "open"
        if item.endswith(("iong", "ong", "ou", "uo", "o")):
            return "round"
        if item.endswith(("u", "v")) or "ue" in item:
            return "tightRound"
        if item.endswith(("i", "in", "ing", "ian", "iang")):
            return "wide"
        if item.endswith(("e", "ei", "en", "eng", "er")):
            return "spread"
        return "spread"

    @staticmethod
    def _consonant_viseme_from_reading(reading: str) -> str:
        item = reading.lower().replace("ü", "v")
        if not item:
            return ""
        if item[0] in {"b", "p", "m"}:
            return "closed"
        if item[0] == "f":
            return "teeth"
        return ""

    @staticmethod
    def _boundary_offset(boundary: dict) -> float:
        return float(boundary.get("offset") or boundary.get("Offset") or 0) / 10_000_000

    @staticmethod
    def _boundary_duration(boundary: dict) -> float:
        return float(boundary.get("duration") or boundary.get("Duration") or 0) / 10_000_000

    @staticmethod
    def _boundary_text(boundary: dict) -> str:
        return str(boundary.get("text") or boundary.get("Text") or "").strip()

    @staticmethod
    def _wav_duration(data: bytes) -> float | None:
        try:
            import io
            import wave

            with wave.open(io.BytesIO(data), "rb") as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate) if rate else None
        except Exception:
            return None

    @staticmethod
    def _read_cache(path: Path) -> bytes | None:
        if path.exists() and path.stat().st_size > 1024:
            return path.read_bytes()
        return None

    @staticmethod
    def _write_cache(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _read_cues(self, path: Path, text: str) -> list[dict]:
        if path.exists() and path.stat().st_size > 0:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list) and len(data) >= max(3, int(len(self._mouth_tokens(text)) * 0.35)):
                    return self._normalize_cues(data)
            except Exception:
                pass
        return self._build_heuristic_cues(text)

    @staticmethod
    def _write_json(path: Path, data: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
