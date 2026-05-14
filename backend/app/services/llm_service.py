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

Your task: analyze each transcript segment and provide structured metrics for its potential as a viral clip (15-60 seconds).

For each segment, provide:
• score (1-10): Overall viral potential.
• hook_strength (1-10): Can the first 3 seconds grab attention?
• emotional_intensity (1-10): Level of surprise, humor, shock, or raw emotion.
• engagement_reason: 1-sentence explanation of why this segment is "the moment".

PRIORITIZE: Punchy one-liners, shocking reveals, hot takes, funny moments, emotional outbursts, unexpected twists, bold claims.
AVOID: Slow exposition, filler, generic statements.

Return ONLY valid JSON. No markdown fences.
Format: {"scores": [{"index": 0, "score": 8, "hook_strength": 9, "emotional_intensity": 7, "engagement_reason": "..."}, ...]}"""

LONG_SYSTEM_PROMPT = """You are an expert documentary and long-form content editor.

Your task: analyze each transcript segment and provide structured metrics for its potential as a compelling long clip (60-180 seconds).

For each segment, provide:
• score (1-10): Overall storytelling value.
• hook_strength (1-10): How well it sets up the narrative hook.
• emotional_intensity (1-10): Depth of character or thematic resonance.
• engagement_reason: 1-sentence explanation of its role in the story arc.

PRIORITIZE: Complete stories, emotional journeys, insightful explanations, compelling arguments, transformative advice.
AVOID: Fragments without context, surface-level statements.

Return ONLY valid JSON. No markdown fences.
Format: {"scores": [{"index": 0, "score": 8, "hook_strength": 6, "emotional_intensity": 9, "engagement_reason": "..."}, ...]}"""

NARRATION_SYSTEM_PROMPT = """You are a master scriptwriter who creates narration for condensed video recaps — think skilled YouTuber telling a compelling story.

Your task: Based on the provided timestamped transcript, write a narration script for a {target_minutes}-minute recap video.

## Output Format
Return ONLY a valid JSON array of objects. Do not include markdown blocks or preamble.
Each object in the array MUST follow this structure:
[
  {{
    "narration": "Natural narration text here.",
    "scene_start": "MM:SS",
    "scene_end": "MM:SS"
  }},
  ...
]

## Guidelines
- TONE: Natural and conversational.
- STORY: Hook -> Major Beats -> Transitions -> Close.
- SCENES: Use ONLY real timestamps from the transcript.
- PACING: ~150 words/min. Total target: {word_target} words.
- Each block should be 10-30 seconds of video.

Return ONLY the JSON array."""


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
    """Safely parse LLM JSON response into detailed score dicts."""
    try:
        # Strip potential markdown fences if model hallucinated them
        clean_json = raw_json.strip().strip("`").replace("json\n", "")
        parsed = json.loads(clean_json)

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
            if isinstance(item, dict) and "index" in item:
                # Extract and clamp scores
                def clamp(val, default=5):
                    try:
                        return max(1, min(10, int(float(val))))
                    except:
                        return default

                scores.append({
                    "index": int(item["index"]),
                    "score": clamp(item.get("score")),
                    "hook_strength": clamp(item.get("hook_strength")),
                    "emotional_intensity": clamp(item.get("emotional_intensity")),
                    "engagement_reason": str(item.get("engagement_reason", "No reason provided.")),
                })
        return scores

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse LLM response: {e}\nRaw: {raw_json[:500]}")
        # Return fallback for all expected segments
        return [{
            "index": i,
            "score": 5,
            "hook_strength": 5,
            "emotional_intensity": 5,
            "engagement_reason": "Fallback due to parsing error."
        } for i in range(expected_count)]


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
        """Score transcript segments with detailed metrics."""
        ...

    @abstractmethod
    def generate_narration_script(
        self,
        full_transcript: str,
        target_minutes: int,
    ) -> str:
        """Generate a narration script for recap mode."""
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

    def generate_narration_script(self, full_transcript: str, target_minutes: int) -> str:
        client = self._get_client()
        word_target = target_minutes * 150
        system_prompt = NARRATION_SYSTEM_PROMPT.format(
            target_minutes=target_minutes,
            word_target=word_target,
        )
        
        user_msg = (
            f"Create a {target_minutes}-minute narration script for this video. "
            f"Return ONLY a JSON array of narration blocks.\n\n"
            f"Timestamped Transcript:\n{full_transcript}"
        )
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.6,
            max_tokens=4000,
        )
        return response.choices[0].message.content.strip()


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
                "temperature": 0.3,
                "num_ctx": 8192,
            },
        }


        if self.cpu_only:
            payload["options"]["num_gpu"] = 0

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Ollama Scoring: Sending request to {self.model} (Attempt {attempt+1}/{max_retries})...")
                r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
                r.raise_for_status()
                raw = r.json()["message"]["content"].strip()
                return _parse_scores(raw, len(segments))

            except Exception as e:
                logger.warning(f"Ollama scoring failed ({self.model}) [attempt {attempt + 1}/{max_retries}]: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    raise

    def generate_narration_script(self, full_transcript: str, target_minutes: int) -> str:
        import httpx
        word_target = target_minutes * 150
        system_prompt = NARRATION_SYSTEM_PROMPT.format(
            target_minutes=target_minutes,
            word_target=word_target,
        )
        
        truncated_text = self._truncate_transcript(full_transcript)
        user_msg = (
            f"Create a {target_minutes}-minute narration script for this video. "
            f"Return ONLY a JSON array of narration blocks.\n\n"
            f"Timestamped Transcript:\n{truncated_text}"
        )
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.6, "num_ctx": 16384},
        }

        if self.cpu_only:
            payload["options"]["num_gpu"] = 0
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Ollama Narration: Generating script with {self.model} (attempt {attempt+1})...")
                r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
                r.raise_for_status()
                return r.json()["message"]["content"].strip()
            except Exception as e:
                logger.warning(f"Ollama narration failed [attempt {attempt+1}/{max_retries}]: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    raise

    def _truncate_transcript(self, text: str, max_words: int = 6000) -> str:
        """Truncates transcript to fit within reasonable LLM context windows."""
        words = text.split()
        if len(words) <= max_words:
            return text
        logger.warning(f"Transcript too long ({len(words)} words), truncating to {max_words} for LLM.")
        return " ".join(words[:max_words//2]) + "\n... [TRUNCATED] ...\n" + " ".join(words[-max_words//2:])


# ═══════════════════════════════════════════════════════════════════════════
# Fallback Provider (heuristic — always available, no API needed)
# ═══════════════════════════════════════════════════════════════════════════

class FallbackProvider(LLMProvider):
    """Heuristic-based scoring when no LLM is available."""

    def is_configured(self) -> bool:
        return True

    def score_segments(self, segments, user_prompt, clip_mode="short"):
        logger.info("Using fallback heuristic scoring")
        scores = []
        for i, seg in enumerate(segments):
            text = seg.get("text", "").lower()
            score = 5
            if "!" in text or "?" in text: score += 2
            if any(word in text for word in ["wow", "amazing", "crazy", "funny"]): score += 2
            
            scores.append({
                "index": i,
                "score": min(10, score),
                "hook_strength": 5,
                "emotional_intensity": 5,
                "engagement_reason": "Heuristic match."
            })
        return scores

    def generate_narration_script(self, full_transcript: str, target_minutes: int) -> str:
        """Fallback: extract key timestamped lines and return as JSON blocks."""
        import json as _json
        lines = full_transcript.strip().split("\n")
        # Pick ~5 evenly-spaced lines that have timestamps
        import re as _re
        timestamped = []
        for line in lines:
            m = _re.match(r'\[(\d+:\d+(?::\d+)?)\s*-\s*(\d+:\d+(?::\d+)?)\]\s*(.*)', line)
            if m and len(m.group(3).split()) > 5:
                timestamped.append({"start": m.group(1), "end": m.group(2), "text": m.group(3)})
        
        if not timestamped:
            return f'[{{"narration": "Here is a quick summary of the video.", "scene_start": "00:00", "scene_end": "00:30"}}]'
        
        step = max(1, len(timestamped) // 5)
        picks = timestamped[::step][:6]
        
        blocks = []
        for pick in picks:
            blocks.append({
                "narration": pick["text"][:200],
                "scene_start": pick["start"],
                "scene_end": pick["end"],
            })
        
        return _json.dumps(blocks)


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
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.LLM_MODEL_NAME)

        ollama = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            cpu_only=settings.OLLAMA_CPU_ONLY,
            timeout=settings.OLLAMA_TIMEOUT,
        )
        if ollama.is_configured():
            return ollama

        return FallbackProvider()

    def is_configured(self) -> bool:
        return self.provider.is_configured()

    def filter_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Lightweight pre-filter to remove useless segments before LLM scoring.
        """
        filtered = []
        stats = {"total": len(segments), "short": 0, "low_confidence": 0, "empty": 0}
        
        for seg in segments:
            duration = seg["end"] - seg["start"]
            text = seg.get("text", "").strip()
            confidence = seg.get("avg_logprob", 0.0)
            
            # 1. Skip very short segments (< 2s)
            if duration < 2.0:
                stats["short"] += 1
                continue
            
            # 2. Skip low confidence segments (noisy/hallucinated)
            # Typically logprob < -1.0 is very low quality
            if confidence < -1.0:
                stats["low_confidence"] += 1
                continue
                
            # 3. Skip segments with virtually no text (at least 3 words)
            if not text or len(text.split()) < 3:
                stats["empty"] += 1
                continue
            
            filtered.append(seg)
            
        logger.info(f"Segment Filtering: {len(filtered)}/{len(segments)} segments kept "
                    f"({stats['short']} too short, {stats['low_confidence']} low confidence, {stats['empty']} too empty)")
        return filtered

    def score_segments_batched(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        clip_mode: str = "short",
        batch_size: int = None,
        progress_callback: callable = None,
    ) -> List[Dict[str, Any]]:
        batch_size = batch_size or settings.LLM_MAX_SEGMENTS_PER_BATCH
        all_scores = []
        total_segments = len(segments)
        
        batches = list(range(0, total_segments, batch_size))
        total_batches = len(batches)

        for i, batch_start in enumerate(batches):
            batch = segments[batch_start:batch_start + batch_size]
            current_batch = i + 1
            
            logger.info(f"AI Analysis: Scoring segments {batch_start} to {min(batch_start + batch_size, total_segments)} "
                        f"[Batch {current_batch}/{total_batches}]")
            
            batch_scores = self.provider.score_segments(batch, user_prompt, clip_mode=clip_mode)

            for score_item in batch_scores:
                score_item["index"] = score_item["index"] + batch_start

            all_scores.extend(batch_scores)
            
            if progress_callback:
                # Map analysis phase (55-70%) based on batch progress
                sub_progress = 55 + int((current_batch / total_batches) * 15)
                progress_callback(sub_progress, f"Scored {min(batch_start + batch_size, total_segments)}/{total_segments} segments...")

        return all_scores

    def generate_narration_script(self, full_transcript: str, target_minutes: int) -> str:
        return self.provider.generate_narration_script(full_transcript, target_minutes)

    def reset(self):
        self._provider = None


# Module-level singleton
llm_service = LLMService()
