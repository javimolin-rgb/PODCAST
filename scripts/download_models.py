from huggingface_hub import snapshot_download
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "kokoro"

print("Downloading Kokoro-82M model and official voice files...")
snapshot_download(
    repo_id="hexgrad/Kokoro-82M",
    local_dir=str(MODEL_DIR),
    allow_patterns=[
        "config.json",
        "*.safetensors",
        "*.json",
        "voices/*.pt",
        "voices/*.bin",
        "voices/*.safetensors",
        "VOICES.md",
    ],
)
print(f"Done. Files stored in {MODEL_DIR}")
