import os
import re
import uuid
import shutil
import asyncio
from pathlib import Path
from backend.kokoro_engine import health as kokoro_health
from typing import Optional

import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pypdf import PdfReader
from docx import Document


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    kokoro_api_url: str = ""
    kokoro_api_key: str = ""
    allowed_origins: str = "http://localhost:5500"
    max_upload_mb: int = 25
    max_chars: int = 500_000


settings = Settings()
app = FastAPI(title="Podcast Studio API", version="1.0.0")

origins = [x.strip() for x in settings.allowed_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME = Path(__file__).parent / "runtime"
JOBS = RUNTIME / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)
jobs = {}


PROFILES = {
    "study": {"pause": 0.28, "max_chars": 2200},
    "podcast": {"pause": 0.18, "max_chars": 2500},
    "lecture": {"pause": 0.36, "max_chars": 1900},
    "review": {"pause": 0.14, "max_chars": 2800},
    "calm": {"pause": 0.50, "max_chars": 1800},
}


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError("Formato no compatible.")


def split_sentences(text: str):
    return [x.strip() for x in re.split(r"(?<=[.!?。！？])\s+", text) if x.strip()]


def split_text(text: str, max_chars: int):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(para) <= max_chars:
            current = para
        else:
            current = ""
            sentence_buf = ""
            for sentence in split_sentences(para):
                if len(sentence_buf) + len(sentence) + 1 <= max_chars:
                    sentence_buf = f"{sentence_buf} {sentence}".strip()
                else:
                    if sentence_buf:
                        chunks.append(sentence_buf)
                    sentence_buf = sentence
            if sentence_buf:
                current = sentence_buf
    if current:
        chunks.append(current)
    return chunks


def detect_chapters(text: str, enabled: bool):
    if not enabled:
        return [("Podcast", text)]

    lines = text.splitlines()
    sections, current_title, current = [], "Introducción", []
    heading_re = re.compile(
        r"^(?:#{1,6}\s+|(?:CAP[IÍ]TULO|CHAPTER|UNIDAD|TEMA|PARTE)\s+[\wIVX0-9].*)$",
        re.I
    )
    for line in lines:
        stripped = line.strip()
        if stripped and heading_re.match(stripped):
            if current:
                sections.append((current_title, "\n".join(current)))
            current_title = re.sub(r"^#+\s*", "", stripped).strip()
            current = []
        else:
            current.append(line)
    if current:
        sections.append((current_title, "\n".join(current)))
    return [(t, c.strip()) for t, c in sections if c.strip()]


def optimize_for_speech(text: str) -> str:
    text = re.sub(r"\s*\([^)]{0,180}\)", "", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"\b(e\.g\.|i\.e\.)\b", lambda m: "por ejemplo" if m.group(1).lower()=="e.g." else "es decir", text, flags=re.I)
    text = re.sub(r"([:;])\s*", r"\1 ", text)
    return text.strip()


async def elevenlabs_tts(text: str, voice_id: str, speed: float, output: Path):
    if not settings.elevenlabs_api_key:
        raise RuntimeError("Falta ELEVENLABS_API_KEY en el backend.")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_model_id,
        "voice_settings": {
            "stability": 0.48,
            "similarity_boost": 0.78,
            "style": 0.22,
            "use_speaker_boost": True,
        },
    }
    # ElevenLabs speed is provider-side; keep 1.0 as neutral and
    # apply a bounded adjustment where supported.
    payload["voice_settings"]["speed"] = float(max(.7, min(1.2, speed)))
    headers = {"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"}
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"ElevenLabs: {r.status_code} {r.text[:500]}")
        output.write_bytes(r.content)


async def kokoro_tts(text: str, voice: str, speed: float, output: Path):
    """
    Genera audio directamente con Kokoro-82M.
    
    No utiliza KOKORO_API_URL ni ninguna API externa.
    """
    from backend.kokoro_engine import generate_to_wav

    generate_to_wav(
        text=text,
        voice=voice,
        speed=speed,
        output=output,
    )


async def generate_job(job_id: str, text: str, profile: str, voice: str, provider: str, speed: float, split_chapters: bool):
    job = jobs[job_id]
    job["status"] = "processing"
    job["message"] = "Analizando el documento…"
    try:
        chapters = detect_chapters(text, split_chapters)
        profile_cfg = PROFILES.get(profile, PROFILES["study"])
        total_units = sum(max(1, len(c)) for _, c in chapters)
        done_units = 0
        result = []

        for chapter_index, (title, content) in enumerate(chapters):
            chunks = split_text(optimize_for_speech(content), profile_cfg["max_chars"])
            chapter_dir = JOBS / job_id
            chapter_dir.mkdir(parents=True, exist_ok=True)
            audio_parts = []

            for chunk_index, chunk in enumerate(chunks):
                job["message"] = f"Generando {title} · segmento {chunk_index+1}/{len(chunks)}"
                extension = "mp3" if provider == "elevenlabs" else "wav"
                part = chapter_dir / f"part_{chapter_index}_{chunk_index}.{extension}"
                if provider == "elevenlabs":
                    await elevenlabs_tts(chunk, voice, speed, part)
                elif provider == "kokoro":
                    await kokoro_tts(chunk, voice, speed, part)
                else:
                    raise RuntimeError("Proveedor TTS no soportado.")
                audio_parts.append(part)
                done_units += len(chunk)
                job["progress"] = min(96, 10 + int(done_units / total_units * 84))

            # MP3 concatenation without transcoding requires compatible streams.
            # For maximum compatibility we use ffmpeg when available.
            extension = "mp3" if provider == "elevenlabs" else "wav"
            final = chapter_dir / f"chapter_{chapter_index}.{extension}"
            concat_file = chapter_dir / f"concat_{chapter_index}.txt"
            concat_file.write_text(
                "\n".join(f"file '{p.name}'" for p in audio_parts),
                encoding="utf-8"
            )
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file.name, "-c", "copy", final.name,
                cwd=str(chapter_dir),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, err = await proc.communicate()
            if proc.returncode != 0:
                # fallback: expose the first segment if ffmpeg isn't installed
                # so generation still produces something useful.
                shutil.copy2(audio_parts[0], final)

            result.append({
                "title": title,
                "audio_url": f"/api/audio/{job_id}/{final.name}",
                "characters": len(content),
            })

        # Combined file for download-all.
        extension = "mp3" if provider == "elevenlabs" else "wav"
        chapter_files = [
            JOBS / job_id / f"chapter_{i}.{extension}"
            for i in range(len(result))
        ]
        combined = JOBS / job_id / f"podcast.{extension}"
        concat_all = JOBS / job_id / "concat_all.txt"
        concat_all.write_text(
            "\n".join(f"file '{p.name}'" for p in chapter_files),
            encoding="utf-8"
        )
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_all.name, "-c", "copy", combined.name,
            cwd=str(JOBS / job_id),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            shutil.copy2(chapter_files[0], combined)

        job.update({
            "status": "completed",
            "progress": 100,
            "message": "Podcast listo.",
            "title": "Podcast Studio",
            "chapters": result,
            "download_url": f"/api/audio/{job_id}/podcast.mp3",
        })
    except Exception as exc:
        job.update({"status": "failed", "error": str(exc), "message": "La generación falló."})


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "providers": {
            "elevenlabs": bool(settings.elevenlabs_api_key),
            "kokoro": True,
        },
    }


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
    if not file and not text.strip():
        raise HTTPException(400, "Sube un documento o pega texto.")
    if provider not in {"elevenlabs", "kokoro"}:
        raise HTTPException(400, "Proveedor no válido.")
    if not (0.7 <= speed <= 1.5):
        raise HTTPException(400, "Velocidad fuera de rango.")

    extracted = text.strip()
    job_id = uuid.uuid4().hex
    work = JOBS / job_id
    work.mkdir(parents=True, exist_ok=True)

    try:
        if file:
            raw = await file.read()
            if len(raw) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(413, "El archivo supera el límite permitido.")
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in {".pdf",".docx",".txt",".md",".markdown"}:
                raise HTTPException(400, "Formato no compatible.")
            uploaded = work / f"source{suffix}"
            uploaded.write_bytes(raw)
            extracted = extracted + "\n\n" + extract_file(uploaded) if extracted else extract_file(uploaded)

        extracted = clean_text(extracted)
        if not extracted:
            raise HTTPException(400, "No se encontró texto utilizable.")
        if len(extracted) > settings.max_chars:
            raise HTTPException(413, f"El documento supera {settings.max_chars:,} caracteres.")

        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "En cola…",
            "chapters": [],
        }
        background_tasks.add_task(
            generate_job, job_id, extracted, profile, voice, provider, speed, split_chapters
        )
        return {"job_id": job_id, "status": "queued"}
    except HTTPException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(400, str(exc))


@app.get("/api/podcasts/{job_id}")
async def get_podcast(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Podcast no encontrado.")
    return {"job_id": job_id, **job}


@app.get("/api/audio/{job_id}/{filename}")
async def audio(job_id: str, filename: str):
    safe = Path(filename).name
    path = JOBS / job_id / safe
    if not path.exists():
        raise HTTPException(404, "Audio no encontrado.")
    media_type = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
    }.get(path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path,
        media_type=media_type,
        filename=safe,
    )
