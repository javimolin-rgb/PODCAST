
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from kokoro_onnx import Kokoro
from misaki.espeak import EspeakG2P


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "kokoro-v1.0.int8.onnx"
VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

SAMPLE_RATE = 24000

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


def validate_model_files():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Kokoro ONNX model not found: {MODEL_PATH}"
        )

    if not VOICES_PATH.exists():
        raise FileNotFoundError(
            f"Kokoro voice pack not found: {VOICES_PATH}"
        )


def get_language_for_voice(voice: str) -> str:
    if not voice or "_" not in voice:
        raise ValueError(f"Invalid Kokoro voice: {voice}")

    prefix = voice.split("_", 1)[0]

    if prefix not in LANGUAGES:
        raise ValueError(f"Unsupported Kokoro voice language: {voice}")

    return LANGUAGES[prefix]


def validate_voice(voice: str):
    if voice not in ALL_VOICES:
        raise ValueError(
            f"Unknown Kokoro voice '{voice}'. "
            f"Available voices: {len(ALL_VOICES)}"
        )


@lru_cache(maxsize=1)
def get_kokoro() -> Kokoro:
    validate_model_files()

    print("[KOKORO-ONNX] Loading INT8 model...")
    print(f"[KOKORO-ONNX] Model: {MODEL_PATH}")
    print(f"[KOKORO-ONNX] Voices: {VOICES_PATH}")

    engine = Kokoro(
        str(MODEL_PATH),
        str(VOICES_PATH),
    )

    print("[KOKORO-ONNX] Engine ready.")

    return engine


@lru_cache(maxsize=8)
def get_g2p(language: str):
    print(f"[KOKORO-ONNX] Loading G2P: {language}")

    return EspeakG2P(language=language)


def phonemize(text: str, language: str) -> str:
    g2p = get_g2p(language)

    phonemes, _ = g2p(text)

    return phonemes


def generate_audio(
    text: str,
    voice: str = "ef_dora",
    speed: float = 1.0,
) -> np.ndarray:

    validate_voice(voice)

    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    language = get_language_for_voice(voice)

    speed = float(speed)

    if speed <= 0:
        speed = 1.0

    if speed < 0.5:
        speed = 0.5

    if speed > 2.0:
        speed = 2.0

    print(
        f"[KOKORO-ONNX] Generating | "
        f"voice={voice} | "
        f"language={language} | "
        f"speed={speed} | "
        f"chars={len(text)}"
    )

    engine = get_kokoro()

    phonemes = phonemize(
        text,
        language,
    )

    if not phonemes:
        raise RuntimeError(
            "Kokoro phonemization returned empty output."
        )

    samples, sample_rate = engine.create(
        phonemes,
        voice=voice,
        speed=speed,
        is_phonemes=True,
    )

    if sample_rate != SAMPLE_RATE:
        print(
            f"[KOKORO-ONNX] Warning: "
            f"sample rate returned: {sample_rate}"
        )

    return np.asarray(samples, dtype=np.float32)


def generate_to_wav(
    text: str,
    voice: str,
    speed: float,
    output: Path,
):
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
        f"[KOKORO-ONNX] Audio saved: "
        f"{output} "
        f"({output.stat().st_size / 1024:.1f} KB)"
    )

    return output


def list_voices():
    return sorted(ALL_VOICES)


def health():
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
