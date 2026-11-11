from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure media directories exist
    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / "subtitles").mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / "visuals").mkdir(parents=True, exist_ok=True)
    (settings.MEDIA_DIR / "renders").mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Static files for rendered media preview
media_path = Path(settings.MEDIA_DIR)
if media_path.exists():
    app.mount("/media", StaticFiles(directory=str(media_path)), name="media")

# Register V1 API Routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to DASMO Office AI YouTube Shorts Factory API",
        "docs": f"{settings.API_V1_STR}/docs",
    }
