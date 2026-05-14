import httpx
import time

try:
    print("Checking Ollama availability...")
    r = httpx.get("http://localhost:11434/api/tags", timeout=5)
    print(f"Ollama status: {r.status_code}")
    print(f"Models: {r.json()}")
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": "Say hello",
        "stream": False
    }
    print("Testing qwen2.5:7b response...")
    start = time.time()
    r = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=30)
    print(f"Response ({round(time.time()-start, 2)}s): {r.json().get('response')}")
except Exception as e:
    print(f"Ollama check failed: {e}")
