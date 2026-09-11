# Podcast Studio Local — TTS para estudiar

Aplicación local para convertir textos largos en podcasts de estudio sin depender de APIs de pago.

## Motor recomendado

**Kokoro-82M** es el motor principal porque tiene buen equilibrio entre calidad, velocidad y tamaño, licencia Apache-2.0 y un catálogo amplio de voces. El proyecto expone las voces oficiales del modelo.

Incluye:
- 54 voces Kokoro.
- Español: `ef_dora` y `em_alex` / `em_santa`.
- Perfiles de narración: Estudio, Podcast, Cátedra, Conversacional, Energético, Calmado y Repaso.
- Segmentación inteligente de textos largos.
- Pausas naturales.
- Control de velocidad.
- Exportación WAV.
- Cola de capítulos.
- Importación TXT, MD, PDF y DOCX (PDF/DOCX requieren las dependencias indicadas).

## Instalación

Recomendado: Python 3.11 o 3.12.

```bash
cd podcast-studio
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_models.py
python app/server.py
```

Luego abre:
http://127.0.0.1:8765

La primera descarga de Kokoro requiere internet. Después el modelo y las voces quedan almacenados localmente.

## macOS Apple Silicon

PyTorch puede usar MPS cuando está disponible. Si MPS da problemas, la app cae a CPU.

## Modelos

### Kokoro — incluido como motor principal
Apache-2.0. Catálogo de voces en:
https://huggingface.co/hexgrad/Kokoro-82M

### Piper — fallback rápido
MIT para el software, pero **cada voz puede tener su propia licencia**. La aplicación deja el mecanismo preparado para añadir voces Piper y leer su MODEL_CARD antes de habilitarlas.

### Chatterbox / F5-TTS — opcionales
No se instalan automáticamente porque sus pesos tienen condiciones de licencia distintas. Chatterbox es MIT en la implementación consultada; F5-TTS tiene código MIT pero pesos CC-BY-NC. Si el uso pasa a ser comercial, revisa las licencias antes de incorporarlos.

## Importante sobre "todas las voces"

La app no copia indiscriminadamente voces de terceros. Descarga las voces oficiales de Kokoro y muestra sus metadatos/licencia. También permite añadir modelos compatibles posteriormente.

Para estudiar, la configuración inicial recomienda voces con ritmo estable y claridad antes que una voz extremadamente expresiva.
