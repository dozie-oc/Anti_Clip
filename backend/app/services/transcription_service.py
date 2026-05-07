import whisper
import os
import torch

class TranscriptionService:
    def __init__(self, model_name="base"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_name, device=self.device)

    def transcribe(self, audio_path: str):
        """
        Transcribe audio file and return segments with timestamps.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        result = self.model.transcribe(audio_path)
        return result['segments']

transcription_service = TranscriptionService()
