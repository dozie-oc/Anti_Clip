"""Full reproduction of the whisper transcription error."""
import traceback
import os
import sys

# Simulate what transcription_service does
try:
    print("Step 1: Importing whisper...")
    import whisper
    print(f"  whisper version: {whisper.__version__}")

    print("Step 2: Importing transformers...")
    import transformers
    print(f"  transformers version: {transformers.__version__}")

    print("Step 3: Checking GPT2Tokenizer attributes...")
    from transformers import GPT2Tokenizer
    for attr in ['additional_special_tokens', 'additional_special_tokens_ids']:
        print(f"  hasattr(GPT2Tokenizer, '{attr}'): {hasattr(GPT2Tokenizer, attr)}")

    print("Step 4: Loading whisper model...")
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  device: {device}")
    model = whisper.load_model("base", device=device)
    print("  Model loaded OK")

    print("Step 5: Testing transcription on a short audio...")
    # Find any wav file in temp
    test_files = []
    for root, dirs, files in os.walk(r"c:\Users\New\Desktop\Pie\Anti_Clip\storage"):
        for f in files:
            if f.endswith(('.wav', '.mp4', '.mkv')):
                test_files.append(os.path.join(root, f))
    
    if test_files:
        print(f"  Found test file: {test_files[0]}")
        # Just try to transcribe first 30 seconds
        result = model.transcribe(test_files[0], verbose=False)
        segs = result.get("segments", [])
        print(f"  Transcription returned {len(segs)} segments")
        if segs:
            print(f"  First segment: {segs[0]}")
    else:
        print("  No test files found, trying with blank audio...")
        import numpy as np
        audio = np.zeros(16000 * 5, dtype=np.float32)  # 5 seconds of silence
        result = model.transcribe(audio, verbose=False)
        print(f"  Transcription returned {len(result.get('segments', []))} segments")

    print("\n✅ ALL STEPS PASSED")

except Exception as e:
    print(f"\n❌ FAILED at: {e}")
    traceback.print_exc()
