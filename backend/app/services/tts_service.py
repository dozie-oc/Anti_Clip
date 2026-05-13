"""
TTS Service — handles local high-quality voice generation using Piper.
"""
import logging
import os
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """Generates speech from text using the Piper TTS engine."""

    def __init__(self):
        self._voice_model = settings.PIPER_VOICE
        self._models_dir = settings.PIPER_MODELS_DIR
        os.makedirs(self._models_dir, exist_ok=True)

    def generate_speech(self, text: str, output_path: str) -> str:
        """
        Synthesizes text to speech and saves as a WAV file.
        """
        try:
            from piper.voice import PiperVoice
            
            # Paths to model and config
            model_path = os.path.join(self._models_dir, f"{self._voice_model}.onnx")
            config_path = os.path.join(self._models_dir, f"{self._voice_model}.onnx.json")

            if not os.path.exists(model_path):
                logger.error(f"Piper model not found at {model_path}. Please download it.")
                raise FileNotFoundError(f"Missing Piper model: {self._voice_model}")

            logger.info(f"Synthesizing speech to {output_path}...")
            
            # Load voice
            voice = PiperVoice.load(model_path, config_path=config_path)
            
            # Open output file and synthesize
            import wave
            with wave.open(output_path, "wb") as wav_file:
                voice.synthesize(text, wav_file)
            
            logger.info("Speech synthesis complete")
            return output_path

        except Exception as e:
            logger.error(f"TTS Synthesis failed: {e}")
            raise


# Module-level singleton
tts_service = TTSService()
