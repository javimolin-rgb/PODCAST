#!/bin/sh
set -eu

mkdir -p models

MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx"
VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin"

if [ ! -s models/kokoro-v1.0.int8.onnx ]; then
    echo "↓ Descargando Kokoro ONNX INT8..."
    curl -L --fail --retry 3 --progress-bar \
        -o models/kokoro-v1.0.int8.onnx \
        "$MODEL_URL"
else
    echo "✓ Modelo ONNX ya existe"
fi

if [ ! -s models/voices-v1.0.bin ]; then
    echo "↓ Descargando voces Kokoro..."
    curl -L --fail --retry 3 --progress-bar \
        -o models/voices-v1.0.bin \
        "$VOICES_URL"
else
    echo "✓ Archivo de voces ya existe"
fi

echo ""
echo "===== KOKORO ONNX LISTO ====="
ls -lh models/kokoro-v1.0.int8.onnx models/voices-v1.0.bin
