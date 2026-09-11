# Catálogo y estrategia de voces

## 1. Kokoro-82M — motor principal

Licencia del modelo: Apache-2.0.

Catálogo oficial consultado:
- American English: 20 voces
- British English: 8
- Japanese: 5
- Mandarin Chinese: 8
- Spanish: 3
- French: 1
- Hindi: 4
- Italian: 2
- Brazilian Portuguese: 2

La aplicación incluye el catálogo en su selector. Para español, las voces relevantes son `ef_dora`, `em_alex` y `em_santa` según la versión/catalogación actual.

## 2. Piper — fallback

Piper es excelente cuando se prioriza velocidad y bajo consumo. Su ecosistema tiene voces para muchos idiomas, incluyendo español de España y México. El repositorio advierte que cada voz puede tener condiciones de licencia diferentes; por eso no se redistribuyen voces indiscriminadamente.

## 3. Chatterbox

Muy interesante para una futura versión "expresiva":
- multilingüe
- clonación zero-shot
- control de exageración emocional

La licencia de los materiales/modelos debe revisarse antes de distribuirlos dentro de una aplicación comercial. Esta versión no los descarga automáticamente.

## 4. F5-TTS

Muy interesante para naturalidad y voz de referencia. El código es MIT, pero los modelos preentrenados están bajo CC-BY-NC por el dataset de entrenamiento. No se usa como motor predeterminado en una aplicación que pueda terminar siendo comercial.

## Perfiles diseñados para estudio

Los estilos de la interfaz no pretenden afirmar que el modelo tenga seis "personalidades" entrenadas. Son presets de síntesis:
- Estudio: 0.88×
- Podcast: 0.95×
- Cátedra: 0.82×
- Energético: 1.02×
- Calmado: 0.78×
- Repaso: 1.08×

El motor divide el texto en segmentos para evitar el problema de que los textos muy largos se aceleren o pierdan prosodia. El usuario puede cambiar la velocidad sin regenerar el texto.
