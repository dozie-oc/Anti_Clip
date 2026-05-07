"""
LLM Service — Adapter-pattern based LLM integration.

Supports OpenAI API with a pluggable architecture for future providers
(Ollama, Llama, Mistral, etc.)
"""
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base — all future providers implement this
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def score_segments(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
    ) -> List[Dict[str, Any]]:
        """Score transcript segments. Returns list of {index, score}."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider has valid credentials."""
        ...


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------

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

    def score_segments(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
    ) -> List[Dict[str, Any]]:
        """Send segments to GPT and get scores back."""
        if not self.is_configured():
            raise ValueError("OpenAI API key is not configured.")

        client = self._get_client()

        # Build the segment list for the prompt
        segment_text = "\n".join(
            f"[{i}] ({seg['start']:.1f}s – {seg['end']:.1f}s): {seg['text']}"
            for i, seg in enumerate(segments)
        )

        system_prompt = (
            "You are an expert viral video editor and content strategist.\n"
            "You will be given transcript segments from a video and a user request.\n"
            "Score each segment from 1–10 based on:\n"
            "  • Relevance to the user's request\n"
            "  • Emotional impact\n"
            "  • Humor potential\n"
            "  • Engagement and shareability\n"
            "  • Likelihood of becoming a viral short clip\n\n"
            "Return ONLY a valid JSON array. No markdown, no explanation.\n"
            'Format: [{"index": 0, "score": 8}, {"index": 1, "score": 3}, ...]'
        )

        user_message = (
            f"User request: \"{user_prompt}\"\n\n"
            f"Transcript segments:\n{segment_text}"
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )

                raw = response.choices[0].message.content.strip()
                return self._parse_scores(raw, len(segments))

            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    @staticmethod
    def _parse_scores(raw_json: str, expected_count: int) -> List[Dict[str, Any]]:
        """Safely parse the LLM JSON response."""
        try:
            parsed = json.loads(raw_json)

            # Handle both {"scores": [...]} and bare [...]
            if isinstance(parsed, dict):
                # Find the list in the dict values
                for value in parsed.values():
                    if isinstance(value, list):
                        parsed = value
                        break

            if not isinstance(parsed, list):
                raise ValueError(f"Expected list, got {type(parsed)}")

            # Validate and normalize
            scores = []
            for item in parsed:
                if isinstance(item, dict) and "index" in item and "score" in item:
                    scores.append({
                        "index": int(item["index"]),
                        "score": max(1, min(10, int(item["score"]))),
                    })

            return scores

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nRaw: {raw_json}")
            # Fallback: give all segments a neutral score
            return [{"index": i, "score": 5} for i in range(expected_count)]


# ---------------------------------------------------------------------------
# Fallback Provider (no API key needed — heuristic scoring)
# ---------------------------------------------------------------------------

class FallbackProvider(LLMProvider):
    """Heuristic-based scoring when no LLM API key is configured."""

    def is_configured(self) -> bool:
        return True  # Always available

    def score_segments(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
    ) -> List[Dict[str, Any]]:
        """Score segments using text heuristics."""
        logger.info("Using fallback heuristic scoring (no LLM API key configured)")

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
            emotional_markers = ["!", "?", "...", "wow", "amazing", "crazy",
                                 "love", "hate", "funny", "hilarious", "sad",
                                 "angry", "shocked", "incredible", "insane"]
            for marker in emotional_markers:
                if marker in text_lower:
                    score += 1
                    break

            # Clamp to 1-10
            score = max(1, min(10, score))
            scores.append({"index": i, "score": score})

        return scores


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------

class LLMService:
    """Factory that returns the appropriate LLM provider."""

    def __init__(self):
        self._provider: Optional[LLMProvider] = None

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> LLMProvider:
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            logger.info(f"Using OpenAI provider (model: {settings.LLM_MODEL_NAME})")
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.LLM_MODEL_NAME,
            )
        else:
            logger.info("No OpenAI API key found — using fallback heuristic scoring")
            return FallbackProvider()

    def is_configured(self) -> bool:
        return self.provider.is_configured()

    def score_segments_batched(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        batch_size: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Score segments in batches to minimize token usage.
        Returns a flat list of {index, score} dicts with global indices.
        """
        batch_size = batch_size or settings.LLM_MAX_SEGMENTS_PER_BATCH
        all_scores: List[Dict[str, Any]] = []

        for batch_start in range(0, len(segments), batch_size):
            batch = segments[batch_start:batch_start + batch_size]
            logger.info(
                f"Scoring batch {batch_start // batch_size + 1} "
                f"({len(batch)} segments)"
            )

            batch_scores = self.provider.score_segments(batch, user_prompt)

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
