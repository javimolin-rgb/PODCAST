#!/bin/sh

set -eu

mkdir -p models

MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx"
VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin"

MODEL_PATH="models/kokoro-v1.0.int8.onnx"
VOICES_PATH="models/voices-v1.0.bin"

if [ ! -s "$MODEL_PATH" ]; then
    echo "Descargando Kokoro ONNX INT8..."

    curl -L \
        --fail \
        --retry 3 \
        --progress-bar \
        -o "$MODEL_PATH" \
        "$MODEL_URL"
else
    echo "Modelo ONNX ya existe"
fi

if [ ! -s "$VOICES_PATH" ]; then
    echo "Descargando voces Kokoro..."

    curl -L \
        --fail \
        --retry 3 \
        --progress-bar \
        -o "$VOICES_PATH" \
        "$VOICES_URL"
else
    echo "Archivo de voces ya existe"
fi

echo ""
echo "===== KOKORO ONNX LISTO ====="

ls -lh "$MODEL_PATH" "$VOICES_PATH"
