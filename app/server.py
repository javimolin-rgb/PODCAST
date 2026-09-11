from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import tempfile, re, os, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)

app = FastAPI(title="Podcast Studio Local")
app.mount("/static", StaticFiles(directory=str(APP / "static")), name="static")

VOICE_CATALOG = [
    # Kokoro official 54-voice catalog
    ("af_alloy","American English","female","neutral"),
    ("af_aoede","American English","female","expressive"),
    ("af_bella","American English","female","warm"),
    ("af_heart","American English","female","warm"),
    ("af_jessica","American English","female","clear"),
    ("af_kore","American English","female","bright"),
    ("af_nicole","American English","female","soft"),
    ("af_nova","American English","female","bright"),
    ("af_river","American English","female","calm"),
    ("af_sarah","American English","female","clear"),
    ("af_sky","American English","female","light"),
    ("am_adam","American English","male","clear"),
    ("am_echo","American English","male","neutral"),
    ("am_eric","American English","male","clear"),
    ("am_fenrir","American English","male","deep"),
    ("am_liam","American English","male","warm"),
    ("am_michael","American English","male","narrator"),
    ("am_onyx","American English","male","deep"),
    ("am_puck","American English","male","energetic"),
    ("am_santa","American English","male","warm"),
    ("bf_alice","British English","female","clear"),
    ("bf_emma","British English","female","warm"),
    ("bf_isabella","British English","female","soft"),
    ("bf_lily","British English","female","bright"),
    ("bm_daniel","British English","male","clear"),
    ("bm_fable","British English","male","narrator"),
    ("bm_george","British English","male","deep"),
    ("bm_lewis","British English","male","warm"),
    ("ef_dora","Spanish","female","clear"),
    ("em_alex","Spanish","male","clear"),
    ("em_santa","Spanish","male","warm"),
    ("ff_siwis","French","female","clear"),
    ("hf_alpha","Hindi","female","clear"),
    ("hf_beta","Hindi","female","warm"),
    ("hm_omega","Hindi","male","deep"),
    ("hm_psi","Hindi","male","clear"),
    ("if_sara","Italian","female","clear"),
    ("im_nicola","Italian","male","warm"),
    ("jf_alpha","Japanese","female","clear"),
    ("jf_gongitsune","Japanese","female","soft"),
    ("jf_nezumi","Japanese","female","bright"),
    ("jf_tebukuro","Japanese","female","warm"),
    ("jm_kumo","Japanese","male","calm"),
    ("pf_dora","Brazilian Portuguese","female","clear"),
    ("pm_alex","Brazilian Portuguese","male","clear"),
    ("zf_xiaobei","Mandarin Chinese","female","clear"),
    ("zf_xiaoni","Mandarin Chinese","female","warm"),
    ("zf_xiaoxiao","Mandarin Chinese","female","bright"),
    ("zf_xiaoyi","Mandarin Chinese","female","soft"),
    ("zm_yunian","Mandarin Chinese","male","warm"),
    ("zm_yunjian","Mandarin Chinese","male","narrator"),
    ("zm_yunxia","Mandarin Chinese","male","clear"),
    ("zm_yunxi","Mandarin Chinese","male","calm"),
]

@app.get("/")
def index():
    return FileResponse(APP / "static" / "index.html")

@app.get("/api/voices")
def voices():
    return {"engine":"kokoro","license":"Apache-2.0","voices":[
        {"id":v[0],"language":v[1],"gender":v[2],"style":v[3]} for v in VOICE_CATALOG
    ]}

def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext in [".txt", ".md", ".markdown"]:
        return data.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader
        p = TMP / f"upload_{os.getpid()}.pdf"
        p.write_bytes(data)
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(p)).pages)
    if ext == ".docx":
        from docx import Document
        p = TMP / f"upload_{os.getpid()}.docx"
        p.write_bytes(data)
        return "\n".join(x.text for x in Document(str(p)).paragraphs)
    raise ValueError("Formato no compatible. Usa TXT, MD, PDF o DOCX.")

def clean_text(t):
    t = t.replace("\r\n","\n").replace("\r","\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def chunks(text, max_chars=900):
    # Chunking conservador para evitar que el TTS se acelere en párrafos largos.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out=[]
    for p in paragraphs:
        if len(p) <= max_chars:
            out.append(p)
            continue
        sentences = re.split(r"(?<=[.!?…])\s+", p)
        cur=""
        for s in sentences:
            if not cur:
                cur=s
            elif len(cur)+1+len(s) <= max_chars:
                cur += " " + s
            else:
                out.append(cur)
                cur=s
        if cur: out.append(cur)
    return out

@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    try:
        text = clean_text(extract_text(file.filename, data))
        return {"filename":file.filename,"text":text,"characters":len(text),"chunks":len(chunks(text))}
    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=400)

@app.post("/api/generate")
async def generate(
    text: str = Form(...),
    voice: str = Form("ef_dora"),
    speed: float = Form(0.95),
    profile: str = Form("study"),
):
    # This endpoint intentionally runs the model locally.
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np

        if voice not in {x[0] for x in VOICE_CATALOG}:
            raise ValueError("Voz no disponible en el catálogo local.")

        # Spanish uses language code 'e'. Other voices infer their language from prefix.
        lang = {"a":"a","b":"b","e":"e","f":"f","h":"h","i":"i","j":"j","p":"p","z":"z"}.get(voice[0], "e")
        pipeline = KPipeline(lang_code=lang)

        pieces = chunks(clean_text(text))
        audios=[]
        for piece in pieces:
            generator = pipeline(piece, voice=voice, speed=float(speed))
            for _, _, audio in generator:
                audios.append(np.asarray(audio))

        if not audios:
            raise ValueError("No se pudo generar audio.")

        audio = np.concatenate(audios)
        out = TMP / f"podcast_{os.getpid()}_{abs(hash(text))}.wav"
        sf.write(str(out), audio, 24000)
        return FileResponse(str(out), media_type="audio/wav", filename="podcast_estudio.wav")
    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=500)
