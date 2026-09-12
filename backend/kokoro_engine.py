from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Iterator

import numpy as np
import soundfile as sf
from kokoro import KPipeline


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
VOICE_DIR = BASE_DIR / "kokoro" / "voices"

SAMPLE_RATE = 24000


# Kokoro identifica el idioma por la primera letra del voice ID.
LANG_CODES = {
    "a": "a",  # American English
    "b": "b",  # British English
    "e": "e",  # Spanish
    "f": "f",  # French
    "h": "h",  # Hindi
    "i": "i",  # Italian
    "j": "j",  # Japanese
    "p": "p",  # Brazilian Portuguese
    "z": "z",  # Mandarin Chinese
}


# ============================================================
# VOCES OFICIALES KOKORO
# ============================================================

KOKORO_VOICES = {
    # American English
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

    # British English
    "bf_alice",
    "bf_emma",
    "bf_isabella",
    "bf_lily",
    "bm_daniel",
    "bm_fable",
    "bm_george",
    "bm_lewis",

    # Spanish
    "ef_dora",
    "em_alex",
    "em_santa",

    # French
    "ff_siwis",

    # Hindi
    "hf_alpha",
    "hf_beta",
    "hm_omega",
    "hm_psi",

    # Italian
    "if_sara",
    "im_nicola",

    # Japanese
    "jf_alpha",
    "jf_gongitsune",
    "jf_nezumi",
    "jf_tebukuro",
    "jm_kumo",

    # Brazilian Portuguese
    "pf_dora",
    "pm_alex",
    "pm_santa",

    # Mandarin
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
# PIPELINES
# ============================================================

@lru_cache(maxsize=9)
def get_pipeline(lang_code: str) -> KPipeline:
    """
    Carga un pipeline de Kokoro por idioma.

    Se utiliza caché para evitar reconstruir el pipeline
    innecesariamente en cada segmento.
    """

    if lang_code not in LANG_CODES.values():
        raise ValueError(f"Idioma Kokoro no soportado: {lang_code}")

    print(f"[KOKORO] Cargando pipeline para idioma: {lang_code}")

    return KPipeline(
        lang_code=lang_code,
        repo_id="hexgrad/Kokoro-82M",
    )


# ============================================================
# VALIDACIÓN DE VOCES
# ============================================================

def validate_voice(voice: str) -> str:
    """
    Valida que la voz solicitada sea una voz Kokoro conocida.
    """

    voice = (voice or "").strip()

    if voice not in KOKORO_VOICES:
        raise ValueError(
            f"Voz Kokoro no válida: {voice}"
        )

    voice_file = VOICE_DIR / f"{voice}.pt"

    if not voice_file.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de voz: {voice_file}"
        )

    return voice


def get_language_for_voice(voice: str) -> str:
    voice = validate_voice(voice)

    prefix = voice[0]

    try:
        return LANG_CODES[prefix]
    except KeyError:
        raise ValueError(
            f"No existe un idioma configurado para la voz: {voice}"
        )


# ============================================================
# GENERACIÓN
# ============================================================

def generate_audio(
    text: str,
    voice: str,
    speed: float = 1.0,
) -> np.ndarray:
    """
    Genera audio directamente con Kokoro.

    No utiliza ninguna API externa.

    Retorna un numpy array float32 a 24 kHz.
    """

    if not text or not text.strip():
        raise ValueError("El texto está vacío.")

    voice = validate_voice(voice)

    speed = float(speed)

    if speed <= 0:
        raise ValueError("La velocidad debe ser mayor que 0.")

    if speed < 0.5:
        speed = 0.5

    if speed > 2.0:
        speed = 2.0

    lang_code = get_language_for_voice(voice)

    pipeline = get_pipeline(lang_code)

    print(
        f"[KOKORO] Generando | "
        f"voice={voice} | "
        f"lang={lang_code} | "
        f"speed={speed} | "
        f"chars={len(text)}"
    )

    audio_parts = []

    generator = pipeline(
        text,
        voice=voice,
        speed=speed,
    )

    for result in generator:
        if result.audio is None:
            continue

        audio = result.audio.detach().cpu().numpy()

        if audio.size == 0:
            continue

        audio_parts.append(audio.astype(np.float32))

    if not audio_parts:
        raise RuntimeError(
            "Kokoro no produjo audio."
        )

    audio = np.concatenate(audio_parts)

    return audio


# ============================================================
# GENERACIÓN + ARCHIVO
# ============================================================

def generate_to_wav(
    text: str,
    voice: str,
    speed: float,
    output: Path,
) -> Path:
    """
    Genera audio y lo guarda como WAV.
    """

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    audio = generate_audio(
        text=text,
        voice=voice,
        speed=speed,
    )

    sf.write(
        str(output),
        audio,
        SAMPLE_RATE,
        subtype="PCM_16",
    )

    print(
        f"[KOKORO] Audio guardado: {output} "
        f"({len(audio) / SAMPLE_RATE:.2f}s)"
    )

    return output


# ============================================================
# INFORMACIÓN
# ============================================================

def list_voices() -> list[str]:
    """
    Devuelve las voces Kokoro disponibles físicamente
    en el proyecto.
    """

    available = []

    for voice in sorted(KOKORO_VOICES):
        if (VOICE_DIR / f"{voice}.pt").exists():
            available.append(voice)

    return available


def health() -> dict:
    """
    Estado del motor Kokoro.
    """

    available = list_voices()

    return {
        "engine": "kokoro-native",
        "model": "hexgrad/Kokoro-82M",
        "sample_rate": SAMPLE_RATE,
        "voices_available": len(available),
        "voices_expected": len(KOKORO_VOICES),
        "voice_directory": str(VOICE_DIR),
    }
