# Podcast Studio — GitHub Pages + API

Aplicación web para convertir documentos de estudio en podcasts.

## Arquitectura

- `frontend/`: aplicación estática desplegable en GitHub Pages.
- `backend/`: API FastAPI desplegable en Render, Railway, Fly.io, Cloud Run, etc.
- TTS principal: ElevenLabs mediante API (configurable).
- TTS alternativo: cualquier endpoint compatible con Kokoro mediante `KOKORO_API_URL`.
- Las claves nunca van al frontend.

## 1. Backend local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env y agrega tu API key
uvicorn main:app --reload --port 8000
```

## 2. Frontend local

Desde la carpeta raíz:

```bash
python3 -m http.server 5500 --directory frontend
```

Abre `http://localhost:5500`.

En el frontend, configura temporalmente:

```js
window.PODCAST_API_URL = "http://localhost:8000";
```

También puede definirse en `frontend/config.js`.

## 3. GitHub Pages

Sube el contenido de `frontend/` a GitHub Pages.

La API NO debe publicarse en GitHub Pages.

Edita `frontend/config.js`:

```js
window.PODCAST_API_URL = "https://TU-BACKEND.onrender.com";
```

## 4. Deploy del backend

El backend incluye `Dockerfile` y puede desplegarse en cualquier servicio que soporte Docker.

Variables mínimas:

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_MODEL_ID` (opcional)
- `ALLOWED_ORIGINS` — separa varios dominios con comas

Opcional:

- `KOKORO_API_URL`
- `KOKORO_API_KEY`
- `MAX_UPLOAD_MB`
- `MAX_CHARS`

## Importante

GitHub Pages es sólo frontend. Nunca pongas `ELEVENLABS_API_KEY` en JavaScript del navegador.

## Funciones

- PDF, DOCX, TXT, Markdown
- pegar texto
- extracción de texto
- limpieza
- segmentación inteligente
- capítulos
- perfiles de narración
- voces configurables
- velocidad
- generación por segmentos
- progreso en tiempo real
- reproductor por capítulos
- descarga de MP3
- API REST
- proveedor TTS intercambiable

## Licencias

Kokoro y sus voces deben mantenerse sujetos a sus licencias oficiales. Este proyecto no redistribuye automáticamente modelos de terceros.
