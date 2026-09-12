import os
import re
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional

import httpx
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pypdf import PdfReader
from docx import Document

from backend.kokoro_engine import (
    health as kokoro_health,
    generate_to_wav,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"

    kokoro_api_url: str = ""
    kokoro_api_key: str = ""

    allowed_origins: str = (
        "https://javimolin-rgb.github.io,"
        "http://localhost:5500,"
        "http://127.0.0.1:5500"
    )

    max_upload_mb: int = 25
    max_chars: int = 500_000


settings = Settings()

app = FastAPI(
    title="Podcast Studio API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIOS Y TRABAJOS
# ============================================================

RUNTIME = Path(__file__).parent / "runtime"
JOBS = RUNTIME / "jobs"

JOBS.mkdir(parents=True, exist_ok=True)

# Memoria temporal de trabajos.
# En Render Free se pierde cuando el servicio se reinicia.
jobs = {}


# ============================================================
# PERFILES DE AUDIO
# ============================================================

PROFILES = {
    "study": {
        "pause": 0.28,
        "max_chars": 2200,
    },
    "podcast": {
        "pause": 0.18,
        "max_chars": 2500,
    },
    "lecture": {
        "pause": 0.36,
        "max_chars": 1900,
    },
    "review": {
        "pause": 0.14,
        "max_chars": 2800,
    },
    "calm": {
        "pause": 0.50,
        "max_chars": 1800,
    },
}


# ============================================================
# LIMPIEZA Y EXTRACCION DE TEXTO
# ============================================================

def clean_text(text: str) -> str:
    """
    Limpia caracteres nulos, espacios repetidos y saltos de línea
    innecesarios.
    """
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(
        r"^\s*[-•]\s*",
        "",
        text,
        flags=re.MULTILINE,
    )

    return text.strip()


def extract_file(path: Path) -> str:
    """
    Extrae texto desde TXT, Markdown, PDF o DOCX.
    """
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    if suffix == ".pdf":
        reader = PdfReader(str(path))

        return "\n\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if suffix == ".docx":
        document = Document(str(path))

        return "\n\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    raise ValueError("Formato no compatible.")


# ============================================================
# DIVISION DEL TEXTO
# ============================================================

def split_sentences(text: str):
    """
    Divide el texto en oraciones.
    """
    return [
        item.strip()
        for item in re.split(
            r"(?<=[.!?。！？])\s+",
            text,
        )
        if item.strip()
    ]


def split_text(text: str, max_chars: int):
    """
    Divide el texto en fragmentos de tamaño controlado.
    """
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = (
            f"{current}\n\n{paragraph}".strip()
            if current
            else paragraph
        )

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)

        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        current = ""
        sentence_buffer = ""

        for sentence in split_sentences(paragraph):
            candidate_sentence = (
                f"{sentence_buffer} {sentence}".strip()
                if sentence_buffer
                else sentence
            )

            if len(candidate_sentence) <= max_chars:
                sentence_buffer = candidate_sentence
            else:
                if sentence_buffer:
                    chunks.append(sentence_buffer)

                sentence_buffer = sentence

        if sentence_buffer:
            current = sentence_buffer

    if current:
        chunks.append(current)

    return chunks


def detect_chapters(text: str, enabled: bool):
    """
    Detecta capítulos a partir de títulos Markdown o palabras
    como CAPÍTULO, UNIDAD, TEMA, PARTE y sus equivalentes.
    """
    if not enabled:
        return [("Podcast", text)]

    lines = text.splitlines()

    sections = []
    current_title = "Introducción"
    current_lines = []

    heading_regex = re.compile(
        r"^(?:"
        r"#{1,6}\s+"
        r"|(?:CAP[IÍ]TULO|CHAPTER|UNIDAD|TEMA|PARTE)"
        r"\s+[\wIVX0-9].*"
        r")$",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()

        if stripped and heading_regex.match(stripped):
            if current_lines:
                sections.append(
                    (
                        current_title,
                        "\n".join(current_lines),
                    )
                )

            current_title = re.sub(
                r"^#+\s*",
                "",
                stripped,
            ).strip()

            current_lines = []

        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            (
                current_title,
                "\n".join(current_lines),
            )
        )

    return [
        (title, content.strip())
        for title, content in sections
        if content.strip()
    ]


def optimize_for_speech(text: str) -> str:
    """
    Simplifica ciertos elementos que pueden perjudicar la lectura
    en voz alta.
    """
    text = re.sub(
        r"\s*\([^)]{0,180}\)",
        "",
        text,
    )

    text = re.sub(
        r"\[([^\]]+)\]",
        r"\1",
        text,
    )

    def replace_abbreviation(match):
        abbreviation = match.group(1).lower()

        if abbreviation == "e.g.":
            return "por ejemplo"

        return "es decir"

    text = re.sub(
        r"\b(e\.g\.|i\.e\.)\b",
        replace_abbreviation,
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"([:;])\s*",
        r"\1 ",
        text,
    )

    return text.strip()


# ============================================================
# ELEVENLABS
# ============================================================

async def elevenlabs_tts(
    text: str,
    voice_id: str,
    speed: float,
    output: Path,
):
    """
    Genera audio mediante ElevenLabs.
    """
    if not settings.elevenlabs_api_key:
        raise RuntimeError(
            "Falta ELEVENLABS_API_KEY en el backend."
        )

    url = (
        "https://api.elevenlabs.io/v1/text-to-speech/"
        f"{voice_id}"
    )

    payload = {
        "text": text,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {
            "stability": 0.48,
            "similarity_boost": 0.78,
            "style": 0.22,
            "use_speaker_boost": True,
            "speed": float(
                max(
                    0.7,
                    min(1.2, speed),
                )
            ),
        },
    }

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Accept": "audio/mpeg",
    }

    async with httpx.AsyncClient(
        timeout=180
    ) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                "ElevenLabs: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

        output.write_bytes(response.content)


# ============================================================
# KOKORO ONNX
# ============================================================

async def kokoro_tts(
    text: str,
    voice: str,
    speed: float,
    output: Path,
):
    """
    Genera audio con Kokoro ONNX.

    La función síncrona generate_to_wav se ejecuta en un hilo
    para no bloquear el event loop de FastAPI.
    """
    await asyncio.to_thread(
        generate_to_wav,
        text,
        voice,
        speed,
        output,
    )


# ============================================================
# CONCATENACION CON FFMPEG
# ============================================================

async def concatenate_audio_files(
    audio_parts,
    final_path: Path,
    extension: str,
):
    """
    Une los segmentos de audio utilizando FFmpeg.

    Para WAV se especifican explícitamente los parámetros de audio.
    """
    if not audio_parts:
        raise RuntimeError(
            "No se generaron segmentos de audio."
        )

    concat_file = final_path.parent / (
        f"{final_path.stem}_concat.txt"
    )

    concat_file.write_text(
        "\n".join(
            f"file '{part.name}'"
            for part in audio_parts
        ),
        encoding="utf-8",
    )

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_file.name,
    ]

    if extension == "wav":
        command.extend(
            [
                "-ar",
                "24000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
            ]
        )
    else:
        command.extend(
            [
                "-c",
                "copy",
            ]
        )

    command.append(final_path.name)

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(final_path.parent),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, error_output = await process.communicate()

    if process.returncode != 0:
        error_message = error_output.decode(
            "utf-8",
            errors="ignore",
        )

        raise RuntimeError(
            "FFmpeg no pudo unir los archivos: "
            f"{error_message[-1000:]}"
        )

    concat_file.unlink(missing_ok=True)


# ============================================================
# GENERACION DEL PODCAST
# ============================================================

async def generate_job(
    job_id: str,
    text: str,
    profile: str,
    voice: str,
    provider: str,
    speed: float,
    split_chapters: bool,
):
    """
    Procesa un trabajo completo de generación.
    """
    job = jobs[job_id]

    job["status"] = "processing"
    job["message"] = "Analizando el documento…"

    try:
        chapters = detect_chapters(
            text,
            split_chapters,
        )

        profile_config = PROFILES.get(
            profile,
            PROFILES["study"],
        )

        total_units = sum(
            max(1, len(content))
            for _, content in chapters
        )

        done_units = 0
        result = []

        for chapter_index, (title, content) in enumerate(
            chapters
        ):
            optimized_content = optimize_for_speech(
                content
            )

            chunks = split_text(
                optimized_content,
                profile_config["max_chars"],
            )

            if not chunks:
                continue

            chapter_dir = JOBS / job_id
            chapter_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            audio_parts = []

            for chunk_index, chunk in enumerate(chunks):
                job["message"] = (
                    f"Generando {title} · "
                    f"segmento {chunk_index + 1}/"
                    f"{len(chunks)}"
                )

                extension = (
                    "mp3"
                    if provider == "elevenlabs"
                    else "wav"
                )

                part = chapter_dir / (
                    f"part_{chapter_index}_"
                    f"{chunk_index}.{extension}"
                )

                if provider == "elevenlabs":
                    await elevenlabs_tts(
                        chunk,
                        voice,
                        speed,
                        part,
                    )

                elif provider == "kokoro":
                    await kokoro_tts(
                        chunk,
                        voice,
                        speed,
                        part,
                    )

                else:
                    raise RuntimeError(
                        "Proveedor TTS no soportado."
                    )

                audio_parts.append(part)

                done_units += len(chunk)

                job["progress"] = min(
                    96,
                    10 + int(
                        done_units / total_units * 84
                    ),
                )

            extension = (
                "mp3"
                if provider == "elevenlabs"
                else "wav"
            )

            final = chapter_dir / (
                f"chapter_{chapter_index}.{extension}"
            )

            await concatenate_audio_files(
                audio_parts,
                final,
                extension,
            )

            result.append(
                {
                    "title": title,
                    "audio_url": (
                        f"/api/audio/{job_id}/"
                        f"{final.name}"
                    ),
                    "characters": len(content),
                }
            )

        if not result:
            raise RuntimeError(
                "No se pudo generar ningún capítulo."
            )

        # ========================================================
        # ARCHIVO FINAL COMPLETO
        # ========================================================

        extension = (
            "mp3"
            if provider == "elevenlabs"
            else "wav"
        )

        chapter_files = [
            JOBS / job_id / f"chapter_{index}.{extension}"
            for index in range(len(result))
        ]

        combined = JOBS / job_id / (
            f"podcast.{extension}"
        )

        await concatenate_audio_files(
            chapter_files,
            combined,
            extension,
        )

        job.update(
            {
                "status": "completed",
                "progress": 100,
                "message": "Podcast listo.",
                "title": "Podcast Studio",
                "chapters": result,
                "download_url": (
                    f"/api/audio/{job_id}/"
                    f"podcast.{extension}"
                ),
            }
        )

    except Exception as error:
        job.update(
            {
                "status": "failed",
                "error": str(error),
                "message": "La generación falló.",
            }
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health():
    """
    Comprueba que la API y los archivos de Kokoro ONNX
    estén disponibles.
    """
    return {
        "status": "ok",
        "providers": {
            "elevenlabs": bool(
                settings.elevenlabs_api_key
            ),
            "kokoro": True,
        },
        "kokoro_engine": kokoro_health(),
    }


# ============================================================
# CREAR PODCAST
# ============================================================

@app.post("/api/podcasts")
async def create_podcast(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    text: str = Form(""),
    profile: str = Form("study"),
    voice: str = Form("ef_dora"),
    provider: str = Form("kokoro"),
    speed: float = Form(1.0),
    split_chapters: bool = Form(True),
):
    """
    Crea un trabajo de generación de podcast.
    """
    if not file and not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Sube un documento o pega texto.",
        )

    if provider not in {
        "elevenlabs",
        "kokoro",
    }:
        raise HTTPException(
            status_code=400,
            detail="Proveedor no válido.",
        )

    if not 0.7 <= speed <= 1.5:
        raise HTTPException(
            status_code=400,
            detail="Velocidad fuera de rango.",
        )

    extracted = text.strip()

    job_id = uuid.uuid4().hex
    work = JOBS / job_id

    work.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        if file:
            raw = await file.read()

            if len(raw) > (
                settings.max_upload_mb * 1024 * 1024
            ):
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "El archivo supera el límite permitido."
                    ),
                )

            suffix = Path(
                file.filename or ""
            ).suffix.lower()

            if suffix not in {
                ".pdf",
                ".docx",
                ".txt",
                ".md",
                ".markdown",
            }:
                raise HTTPException(
                    status_code=400,
                    detail="Formato no compatible.",
                )

            uploaded = work / f"source{suffix}"
            uploaded.write_bytes(raw)

            file_text = extract_file(uploaded)

            if extracted:
                extracted = (
                    f"{extracted}\n\n{file_text}"
                )
            else:
                extracted = file_text

        extracted = clean_text(extracted)

        if not extracted:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se encontró texto utilizable."
                ),
            )

        if len(extracted) > settings.max_chars:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"El documento supera "
                    f"{settings.max_chars:,} caracteres."
                ),
            )

        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "En cola…",
            "chapters": [],
        }

        background_tasks.add_task(
            generate_job,
            job_id,
            extracted,
            profile,
            voice,
            provider,
            speed,
            split_chapters,
        )

        return {
            "job_id": job_id,
            "status": "queued",
        }

    except HTTPException:
        shutil.rmtree(
            work,
            ignore_errors=True,
        )
        raise

    except Exception as error:
        shutil.rmtree(
            work,
            ignore_errors=True,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# ============================================================
# CONSULTAR ESTADO DEL PODCAST
# ============================================================

@app.get("/api/podcasts/{job_id}")
async def get_podcast(job_id: str):
    """
    Devuelve el estado de un trabajo.
    """
    job = jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Podcast no encontrado.",
        )

    return {
        "job_id": job_id,
        **job,
    }


# ============================================================
# SERVIR AUDIO
# ============================================================

@app.get("/api/audio/{job_id}/{filename}")
async def audio(
    job_id: str,
    filename: str,
):
    """
    Sirve los archivos de audio generados.
    """
    safe_filename = Path(filename).name
    path = JOBS / job_id / safe_filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio no encontrado.",
        )

    media_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
    }.get(
        path.suffix.lower(),
        "application/octet-stream",
    )

    return FileResponse(
        path,
        media_type=media_type,
        filename=safe_filename,
    )
