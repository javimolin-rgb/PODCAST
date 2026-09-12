
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

from kokoro_onnx import Kokoro
from misaki.espeak import EspeakG2P


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "kokoro-v1.0.int8.onnx"

VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

SAMPLE_RATE = 24000


# ============================================================
# IDIOMAS POR PREFIJO DE VOZ
# ============================================================

LANGUAGES = {
    "af": "en-us",
    "am": "en-us",
    "bf": "en-gb",
    "bm": "en-gb",
    "ef": "es",
    "em": "es",
    "ff": "fr-fr",
    "hf": "hi",
    "hm": "hi",
    "if": "it",
    "im": "it",
    "jf": "ja",
    "jm": "ja",
    "pf": "pt-br",
    "pm": "pt-br",
    "zf": "zh",
    "zm": "zh",
}


# ============================================================
# VOCES DISPONIBLES
# ============================================================

ALL_VOICES = {
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",
    "ef_dora",
    "em_alex",
    "em_santa",
    "ff_siwis",
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",
    "if_sara",
    "im_nicola",
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",
    "pf_dora",
    "pm_alex",
    "pm_santa",
    "zf_xiaobei",
    "zf_xiaoni",
    "zf_xiaoxiao",
    "zf_xiaoyi",
    "zm_yunjian",
    "zm_yunxi",
    "zm_yunxia",
    "zm_yunyang",
}


# ============================================================
# VALIDACIONES
# ============================================================

def validate_model_files():
    """
    Comprueba que el modelo ONNX y el archivo de voces existan.
    """

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "No se encontró el modelo Kokoro ONNX: "
            f"{MODEL_PATH}"
        )

    if not VOICES_PATH.exists():
        raise FileNotFoundError(
            "No se encontró el archivo de voces Kokoro: "
            f"{VOICES_PATH}"
        )


def get_language_for_voice(voice: str) -> str:
    """
    Obtiene el idioma a partir del prefijo de la voz.
    """

    if not voice or "_" not in voice:
        raise ValueError(
            f"Voz Kokoro no válida: {voice}"
        )

    prefix = voice.split("_", 1)[0]

    if prefix not in LANGUAGES:
        raise ValueError(
            f"Idioma no compatible para la voz: {voice}"
        )

    return LANGUAGES[prefix]


def validate_voice(voice: str):
    """
    Comprueba que la voz solicitada exista en la lista permitida.
    """

    if voice not in ALL_VOICES:
        raise ValueError(
            f"Voz Kokoro desconocida: '{voice}'. "
            f"Voces disponibles: {len(ALL_VOICES)}"
        )


# ============================================================
# CARGA DEL MOTOR ONNX
# ============================================================

@lru_cache(maxsize=1)
def get_kokoro() -> Kokoro:
    """
    Carga el modelo ONNX una sola vez por proceso.
    """

    validate_model_files()

    print(
        "[KOKORO-ONNX] Cargando modelo INT8...",
        flush=True,
    )

    print(
        f"[KOKORO-ONNX] Modelo: {MODEL_PATH}",
        flush=True,
    )

    print(
        f"[KOKORO-ONNX] Voces: {VOICES_PATH}",
        flush=True,
    )

    engine = Kokoro(
        str(MODEL_PATH),
        str(VOICES_PATH),
    )

    print(
        "[KOKORO-ONNX] Motor listo.",
        flush=True,
    )

    return engine


# ============================================================
# CARGA DEL CONVERSOR TEXTO-FONEMAS
# ============================================================

@lru_cache(maxsize=8)
def get_g2p(language: str):
    """
    Carga y conserva el conversor texto-fonemas por idioma.

    Se agregan mensajes detallados para identificar si el proceso
    se bloquea durante la inicialización de EspeakG2P.
    """

    print(
        f"[KOKORO-ONNX] Cargando G2P: {language}",
        flush=True,
    )

    try:
        print(
            "[KOKORO-ONNX] Antes de inicializar EspeakG2P",
            flush=True,
        )

        g2p = EspeakG2P(
            language=language
        )

        print(
            "[KOKORO-ONNX] EspeakG2P inicializado correctamente",
            flush=True,
        )

        return g2p

    except Exception as exc:
        print(
            "[KOKORO-ONNX] ERROR inicializando EspeakG2P: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        raise


# ============================================================
# FONEMIZACION
# ============================================================

def phonemize(
    text: str,
    language: str,
) -> str:
    """
    Convierte texto a fonemas.
    """

    print(
        "[KOKORO-ONNX] Iniciando fonemización",
        flush=True,
    )

    print(
        f"[KOKORO-ONNX] Idioma de fonemización: {language}",
        flush=True,
    )

    print(
        f"[KOKORO-ONNX] Caracteres a fonemizar: {len(text)}",
        flush=True,
    )

    g2p = get_g2p(language)

    print(
        "[KOKORO-ONNX] Ejecutando G2P sobre el texto",
        flush=True,
    )

    phonemes, tokens = g2p(text)

    print(
        "[KOKORO-ONNX] Fonemización completada",
        flush=True,
    )

    print(
        f"[KOKORO-ONNX] Fonemas generados: {len(phonemes)}",
        flush=True,
    )

    return phonemes


# ============================================================
# GENERACION DE AUDIO
# ============================================================

def generate_audio(
    text: str,
    voice: str = "ef_dora",
    speed: float = 1.0,
) -> np.ndarray:
    """
    Genera audio utilizando Kokoro ONNX.
    """

    validate_voice(voice)

    if not text or not text.strip():
        raise ValueError(
            "El texto no puede estar vacío."
        )

    language = get_language_for_voice(
        voice
    )

    speed = float(speed)

    if speed <= 0:
        speed = 1.0

    speed = max(
        0.5,
        min(2.0, speed),
    )

    print(
        "[KOKORO-ONNX] Generando audio | "
        f"voice={voice} | "
        f"language={language} | "
        f"speed={speed} | "
        f"chars={len(text)}",
        flush=True,
    )

    print(
        "[KOKORO-ONNX] Solicitando motor Kokoro",
        flush=True,
    )

    engine = get_kokoro()

    print(
        "[KOKORO-ONNX] Motor Kokoro disponible",
        flush=True,
    )

    phonemes = phonemize(
        text,
        language,
    )

    if not phonemes:
        raise RuntimeError(
            "La fonemización de Kokoro devolvió un resultado vacío."
        )

    print(
        "[KOKORO-ONNX] Iniciando generación de audio con engine.create",
        flush=True,
    )

    samples, sample_rate = engine.create(
        phonemes,
        voice=voice,
        speed=speed,
        is_phonemes=True,
    )

    print(
        "[KOKORO-ONNX] Generación de audio completada",
        flush=True,
    )

    if sample_rate != SAMPLE_RATE:
        print(
            "[KOKORO-ONNX] Advertencia: "
            f"frecuencia recibida: {sample_rate}",
            flush=True,
        )

    return np.asarray(
        samples,
        dtype=np.float32,
    )


# ============================================================
# GENERACION Y GUARDADO DE WAV
# ============================================================

def generate_to_wav(
    text: str,
    voice: str,
    speed: float,
    output: Path,
):
    """
    Genera audio y lo guarda como WAV PCM16.
    """

    output = Path(output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"[KOKORO-ONNX] Generando archivo WAV: {output}",
        flush=True,
    )

    audio = generate_audio(
        text=text,
        voice=voice,
        speed=speed,
    )

    try:
        sf.write(
            str(output),
            audio,
            SAMPLE_RATE,
            subtype="PCM_16",
        )

    finally:
        # Libera explícitamente el array de audio.
        del audio

    print(
        "[KOKORO-ONNX] Audio guardado: "
        f"{output} "
        f"({output.stat().st_size / 1024:.1f} KB)",
        flush=True,
    )

    return output


# ============================================================
# INFORMACION DEL MOTOR
# ============================================================

def list_voices():
    """
    Devuelve las voces disponibles.
    """

    return sorted(ALL_VOICES)


def health():
    """
    Devuelve información de diagnóstico del motor.
    """

    return {
        "engine": "kokoro-onnx",
        "model": "kokoro-v1.0.int8.onnx",
        "quantization": "int8",
        "sample_rate": SAMPLE_RATE,
        "voices_available": len(ALL_VOICES),
        "voices_expected": 54,
        "model_exists": MODEL_PATH.exists(),
        "voices_file_exists": VOICES_PATH.exists(),
        "memory_optimized": True,
    }
