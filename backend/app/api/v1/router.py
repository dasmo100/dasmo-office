from fastapi import APIRouter
from app.api.v1.endpoints import health, settings, shorts, youtube_auth

api_router = APIRouter()

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(settings.router, prefix="/settings", tags=["System Settings"])
api_router.include_router(shorts.router, prefix="/shorts", tags=["Shorts Pipeline"])
api_router.include_router(youtube_auth.router, prefix="/youtube", tags=["YouTube OAuth2"])
