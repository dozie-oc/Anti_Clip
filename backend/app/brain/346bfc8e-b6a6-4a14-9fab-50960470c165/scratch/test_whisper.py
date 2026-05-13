
import whisper
import torch
try:
    print("Loading whisper model...")
    model = whisper.load_model("base")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
