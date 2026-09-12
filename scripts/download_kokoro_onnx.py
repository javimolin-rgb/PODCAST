from pathlib import Path
from urllib.request import urlopen, Request

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "kokoro-v1.0.int8.onnx":
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",
    "voices-v1.0.bin":
        "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",
}

for filename, url in FILES.items():
    destination = MODELS_DIR / filename

    if destination.exists() and destination.stat().st_size > 0:
        print(f"✓ Ya existe: {filename}")
        continue

    print(f"↓ Descargando: {filename}")

    request = Request(
        url,
        headers={"User-Agent": "PODCAST-Studio/1.0"}
    )

    with urlopen(request, timeout=300) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        with open(destination, "wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break

                f.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded * 100 / total
                    print(
                        f"\r  {percent:5.1f}% "
                        f"({downloaded / 1024 / 1024:.1f} MB)",
                        end="",
                        flush=True
                    )

    print()
    print(f"✓ Descargado: {filename} ({destination.stat().st_size / 1024 / 1024:.1f} MB)")

print()
print("========================================")
print("KOKORO ONNX PREPARADO")
print("========================================")
