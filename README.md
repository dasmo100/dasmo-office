# DASMO Office - Fábrica Automatizada de YouTube Shorts con IA

Monorepo diseñado con arquitectura limpia y orquestación integral en **Docker Compose** para la producción autónoma y aprobación editorial de YouTube Shorts (formato vertical 9:16).

---

## 🏗️ Arquitectura del Sistema

```
dasmo-office/
├── backend/                  # API REST FastAPI (Python 3.11)
│   ├── alembic/              # Migraciones asíncronas para PostgreSQL
│   ├── app/
│   │   ├── api/v1/           # Endpoints: creación, estado y aprobación
│   │   ├── core/             # Configuración Pydantic Settings & constantes
│   │   ├── db/               # SQLAlchemy 2.0 Async engine & modelos base
│   │   ├── models/           # Tablas de PostgreSQL
│   │   ├── schemas/          # Esquemas Pydantic v2
│   │   ├── agents/           # Módulos especializados de IA
│   │   │   ├── researcher.py
│   │   │   ├── scriptwriter_gemini.py
│   │   │   ├── voice_tts.py
│   │   │   ├── visual_generator.py
│   │   │   ├── subtitle_whisper.py
│   │   │   └── ffmpeg_renderer.py
│   │   └── worker/           # Celery Task Queue conectado a Redis
│   └── requirements.txt
├── frontend/                 # Admin Dashboard Next.js (App Router, Tailwind, TS)
│   ├── src/app/              # Vistas de monitor en tiempo real y visor 9:16
│   └── package.json
├── media/                    # Volumen compartido local (audios, .ass, renders)
├── docker/
│   ├── Dockerfile.backend    # Python 3.11 + FFmpeg + Fuentes tipográficas
│   └── Dockerfile.frontend   # Node 20 Alpine
├── docker-compose.yml        # Orquestación multi-contenedor
└── .env.example              # Variables de entorno
```

---

## 🚀 Servicios Orquestados (Docker Compose)

| Contenedor | Servicio / Stack | Puerto | Descripción |
| :--- | :--- | :--- | :--- |
| **`dasmo-api`** | FastAPI (Python 3.11) | `8000` | API principal y servidor estático de `/media` |
| **`dasmo-worker`** | Celery Worker | N/A | Ejecutor en segundo plano del pipeline multi-agente |
| **`dasmo-frontend`** | Next.js 14 (App Router) | `3000` | Consola administrativa y reproductor 9:16 |
| **`dasmo-db`** | PostgreSQL 16 Alpine | `5432` | Base de datos relacional persistente |
| **`dasmo-redis`** | Redis 7 Alpine | `6379` | Broker de mensajes y backend de resultados Celery |

---

## ⚙️ Puesta en Marcha

1. **Clonar y configurar variables de entorno:**
   ```bash
   cp .env.example .env
   ```

2. **Levantar todos los contenedores con Docker Compose:**
   ```bash
   docker compose up --build
   ```

3. **Accesos directos:**
   - **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
   - **FastAPI Swagger Docs:** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - **Healthcheck:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
