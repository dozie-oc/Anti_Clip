"""
LLM Service — Adapter-pattern LLM integration with multi-provider support.

Provider priority:
  1. OpenAI  (paid, highest quality)
  2. Ollama  (free, local — primary recommended)
  3. Fallback (heuristic, always available)
"""
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Mode-aware system prompts
# ═══════════════════════════════════════════════════════════════════════════

SHORT_SYSTEM_PROMPT = """You are an elite short-form video editor who creates viral TikTok, YouTube Shorts, and Instagram Reels.

Your task: score each transcript segment from 1-10 based on its potential as a SHORT viral clip (15-60 seconds).

Scoring rubric (evaluate as a composite):
• Hook Strength — Can the first 3-5 seconds grab attention instantly?
• Emotional Intensity — Surprise, humor, shock, awe, controversy, or raw emotion?
• Shareability — Would someone tag a friend or repost this?
• Pacing & Energy — Fast, dynamic, high-energy delivery?
• Visual Potential — Implies action, strong reactions, expressive moments?

PRIORITIZE: Punchy one-liners, shocking reveals, hot takes, funny moments, emotional outbursts, unexpected twists, bold claims, confrontations.
AVOID: Slow exposition, filler, setup without payoff, generic statements.

Return ONLY valid JSON. No markdown fences, no explanation.
Format: {"scores": [{"index": 0, "score": 8}, {"index": 1, "score": 3}]}"""

LONG_SYSTEM_PROMPT = """You are an expert documentary and long-form content editor.

Your task: score each transcript segment from 1-10 based on its potential as a LONG compelling clip (60-180 seconds).

Scoring rubric (evaluate as a composite):
• Storytelling & Narrative Arc — Does this contain a complete mini-story or coherent argument?
• Emotional Journey — Is there buildup, tension, climax, or resolution?
• Educational / Actionable Value — Does it teach something valuable or provide deep insight?
• Depth & Nuance — Complex ideas, multiple perspectives, expert knowledge?
• Shareability — Valuable enough that someone would bookmark or share it?

PRIORITIZE: Complete stories, emotional journeys, insightful explanations, compelling arguments, "aha" moments with context, transformative advice.
AVOID: Fragments without context, surface-level statements, repetitive points.

Return ONLY valid JSON. No markdown fences, no explanation.
Format: {"scores": [{"index": 0, "score": 8}, {"index": 1, "score": 3}]}"""


def _get_system_prompt(clip_mode: str) -> str:
    """Return the appropriate system prompt for the clip mode."""
    return SHORT_SYSTEM_PROMPT if clip_mode == "short" else LONG_SYSTEM_PROMPT


def _build_user_message(segments: List[Dict], user_prompt: str) -> str:
    """Format segments into a numbered list for the LLM."""
    seg_lines = "\n".join(
        f"[{i}] ({seg['start']:.1f}s – {seg['end']:.1f}s): {seg['text']}"
        for i, seg in enumerate(segments)
    )
    return f'User request: "{user_prompt}"\n\nTranscript segments:\n{seg_lines}'


def _parse_scores(raw_json: str, expected_count: int) -> List[Dict[str, Any]]:
    """Safely parse LLM JSON response into [{index, score}, ...]."""
    try:
        parsed = json.loads(raw_json)

        # Handle {"scores": [...]} wrapper
        if isinstance(parsed, dict):
            for value in parsed.values():
                if isinstance(value, list):
                    parsed = value
                    break

        if not isinstance(parsed, list):
            raise ValueError(f"Expected list, got {type(parsed)}")

        scores = []
        for item in parsed:
            if isinstance(item, dict) and "index" in item and "score" in item:
                scores.append({
                    "index": int(item["index"]),
                    "score": max(1, min(10, int(float(item["score"])))),
                })
        return scores

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse LLM response: {e}\nRaw: {raw_json[:500]}")
        return [{"index": i, "score": 5} for i in range(expected_count)]


# ═══════════════════════════════════════════════════════════════════════════
# Abstract base — all providers implement this
# ═══════════════════════════════════════════════════════════════════════════

class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def score_segments(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        clip_mode: str = "short",
    ) -> List[Dict[str, Any]]:
        """Score transcript segments. Returns list of {index, score}."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider has valid credentials / is reachable."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# OpenAI Provider (paid, highest quality)
# ═══════════════════════════════════════════════════════════════════════════

class OpenAIProvider(LLMProvider):
    """OpenAI GPT-based scoring provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def score_segments(self, segments, user_prompt, clip_mode="short"):
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured.")

        client = self._get_client()
        system_prompt = _get_system_prompt(clip_mode)
        user_message = _build_user_message(segments, user_prompt)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.3 if clip_mode == "short" else 0.4,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                return _parse_scores(raw, len(segments))

            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise


# ═══════════════════════════════════════════════════════════════════════════
# Ollama Provider (free, local — primary recommended)
# ═══════════════════════════════════════════════════════════════════════════

class OllamaProvider(LLMProvider):
    """Local Ollama-based scoring using qwen2.5-coder or similar models."""

    def __init__(self, base_url: str, model: str, cpu_only: bool = False, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.cpu_only = cpu_only
        self.timeout = timeout
        self._available: Optional[bool] = None

    def is_configured(self) -> bool:
        """Check if Ollama is running and the model is available."""
        if self._available is not None:
            return self._available

        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code != 200:
                self._available = False
                return False

            # Check if our model is pulled
            models = [m.get("name", "") for m in r.json().get("models", [])]
            model_found = any(self.model in m for m in models)

            if not model_found:
                logger.warning(
                    f"Ollama is running but model '{self.model}' not found. "
                    f"Available: {models}. Run: ollama pull {self.model}"
                )
                self._available = False
            else:
                self._available = True

        except Exception as e:
            logger.info(f"Ollama not reachable at {self.base_url}: {e}")
            self._available = False

        return self._available

    def score_segments(self, segments, user_prompt, clip_mode="short"):
        """Send segments to Ollama for scoring."""
        import httpx

        system_prompt = _get_system_prompt(clip_mode)
        user_message = _build_user_message(segments, user_prompt)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.4 if clip_mode == "short" else 0.5,
                "num_ctx": 4096,
            },
        }

        # Force CPU-only if configured
        if self.cpu_only:
            payload["options"]["num_gpu"] = 0

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Ollama ({self.model}) scoring {len(segments)} segments "
                    f"[mode={clip_mode}, attempt={attempt + 1}]"
                )
                r = httpx.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                r.raise_for_status()

                raw = r.json()["message"]["content"].strip()
                scores = _parse_scores(raw, len(segments))
                logger.info(f"Ollama returned {len(scores)} scores")
                return scores

            except Exception as e:
                logger.warning(f"Ollama attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    raise


# ═══════════════════════════════════════════════════════════════════════════
# Fallback Provider (heuristic — always available, no API needed)
# ═══════════════════════════════════════════════════════════════════════════

class FallbackProvider(LLMProvider):
    """Heuristic-based scoring when no LLM is available."""

    def is_configured(self) -> bool:
        return True  # Always available

    def score_segments(self, segments, user_prompt, clip_mode="short"):
        """Score segments using text heuristics."""
        logger.info("Using fallback heuristic scoring (no LLM available)")

        prompt_lower = user_prompt.lower()
        prompt_keywords = set(prompt_lower.split())
        scores = []

        for i, seg in enumerate(segments):
            text = seg.get("text", "").strip()
            text_lower = text.lower()
            score = 5  # base score

            # Length bonus — longer dialogue is usually more substantive
            word_count = len(text.split())
            if word_count > 20:
                score += 1
            if word_count > 40:
                score += 1

            # Keyword match bonus
            matching_words = prompt_keywords & set(text_lower.split())
            score += min(len(matching_words), 2)

            # Emotional indicators
            emotional_markers = [
                "!", "?", "...", "wow", "amazing", "crazy",
                "love", "hate", "funny", "hilarious", "sad",
                "angry", "shocked", "incredible", "insane",
            ]
            for marker in emotional_markers:
                if marker in text_lower:
                    score += 1
                    break

            # Clamp to 1-10
            score = max(1, min(10, score))
            scores.append({"index": i, "score": score})

        return scores


# ═══════════════════════════════════════════════════════════════════════════
# Service factory — selects the best available provider
# ═══════════════════════════════════════════════════════════════════════════

class LLMService:
    """Factory that returns the best available LLM provider."""

    def __init__(self):
        self._provider: Optional[LLMProvider] = None

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> LLMProvider:
        # 1. OpenAI (paid, highest quality)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            logger.info(f"Using OpenAI provider (model: {settings.LLM_MODEL_NAME})")
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.LLM_MODEL_NAME,
            )

        # 2. Ollama (free, local — primary recommended)
        ollama = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            cpu_only=settings.OLLAMA_CPU_ONLY,
            timeout=settings.OLLAMA_TIMEOUT,
        )
        if ollama.is_configured():
            logger.info(f"Using Ollama provider (model: {settings.OLLAMA_MODEL})")
            return ollama

        # 3. Fallback heuristic (always available)
        logger.info("No LLM available — using fallback heuristic scoring")
        return FallbackProvider()

    def is_configured(self) -> bool:
        return self.provider.is_configured()

    def score_segments_batched(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        clip_mode: str = "short",
        batch_size: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Score segments in batches to manage token/context limits.
        Returns a flat list of {index, score} dicts with global indices.
        """
        batch_size = batch_size or settings.LLM_MAX_SEGMENTS_PER_BATCH
        all_scores: List[Dict[str, Any]] = []

        for batch_start in range(0, len(segments), batch_size):
            batch = segments[batch_start:batch_start + batch_size]
            logger.info(
                f"Scoring batch {batch_start // batch_size + 1} "
                f"({len(batch)} segments, mode={clip_mode})"
            )

            batch_scores = self.provider.score_segments(
                batch, user_prompt, clip_mode=clip_mode
            )

            # Remap indices to global
            for score_item in batch_scores:
                score_item["index"] = score_item["index"] + batch_start

            all_scores.extend(batch_scores)

        return all_scores

    def reset(self):
        """Force re-creation of provider (e.g., after config change)."""
        self._provider = None


# Module-level singleton
llm_service = LLMService()
