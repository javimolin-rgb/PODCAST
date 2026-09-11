# Deploy rápido

## Render

1. Crea un Web Service apuntando al repositorio.
2. Root Directory: `backend`
3. Runtime: Docker
4. Agrega las variables del `.env.example`.
5. Usa como URL del servicio la que entregue Render.
6. Pon esa URL en `frontend/config.js`.

### Recomendación

Para uso público real, usa un servicio persistente/worker en lugar de depender de un free tier con suspensión, porque la generación de audio puede tardar varios minutos.

## ffmpeg

El Dockerfile de esta primera versión necesita `ffmpeg` para concatenar los segmentos. En una imagen Debian/Ubuntu agrega:

```dockerfile
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

Si tu plataforma ya lo incluye, no necesitas modificarlo.
