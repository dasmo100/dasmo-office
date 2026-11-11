import logging
from typing import Optional
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dynamic_settings import get_or_create_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

YOUTUBE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


@router.get("/auth-url", summary="Generar URL de autorización OAuth2 de YouTube")
async def get_youtube_auth_url():
    """Genera la URL oficial de consentimiento de Google OAuth2 para autorizar
    la subida automática de videos a YouTube.
    """
    client_id = settings.YOUTUBE_CLIENT_ID
    if not client_id:
        return {
            "configured": False,
            "auth_url": None,
            "message": "Falta configurar YOUTUBE_CLIENT_ID y YOUTUBE_CLIENT_SECRET en .env",
        }

    redirect_uri = "http://localhost:8000/api/v1/youtube/callback"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(YOUTUBE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    url = f"{YOUTUBE_OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {
        "configured": True,
        "auth_url": url,
        "redirect_uri": redirect_uri,
    }


@router.get("/callback", response_class=HTMLResponse, summary="Callback OAuth2 de Google")
async def youtube_oauth_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Recibe el código temporal de Google, intercambia por tokens, guarda
    el refresh_token en PostgreSQL (system_settings) y muestra feedback al usuario.
    """
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body style="background:#090D16;color:#f87171;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
                    <div style="background:#18181b;border:1px solid #7f1d1d;padding:30px;border-radius:12px;text-align:center;">
                        <h2>Error en la Autorización de YouTube</h2>
                        <p>{error}</p>
                    </div>
                </body>
            </html>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Falta el parámetro 'code'.")

    client_id = settings.YOUTUBE_CLIENT_ID
    client_secret = settings.YOUTUBE_CLIENT_SECRET
    redirect_uri = "http://localhost:8000/api/v1/youtube/callback"

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_resp = await client.post(
            YOUTUBE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error("Failed to exchange code for tokens: %s", token_resp.text)
        return HTMLResponse(
            content=f"""
            <html>
                <body style="background:#090D16;color:#f87171;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
                    <div style="background:#18181b;border:1px solid #7f1d1d;padding:30px;border-radius:12px;text-align:center;">
                        <h2>Error canjeando credenciales con Google</h2>
                        <pre style="color:#ef4444;font-size:12px;">{token_resp.text}</pre>
                    </div>
                </body>
            </html>
            """,
            status_code=400,
        )

    tokens = token_resp.json()
    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        logger.warning("No refresh_token returned by Google (was already authorized without prompt=consent?)")

    # Persist in PostgreSQL
    system_setting = await get_or_create_settings(db)
    if refresh_token:
        system_setting.youtube_refresh_token = refresh_token
        await db.commit()
        await db.refresh(system_setting)

    logger.info("Successfully linked YouTube OAuth channel in PostgreSQL!")

    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
            <head>
                <title>YouTube Conectado | DASMO Office</title>
                <meta charset="utf-8">
            </head>
            <body style="background:#090D16;color:#f4f4f5;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
                <div style="background:#18181b;border:1px solid #27272a;padding:40px;border-radius:16px;text-align:center;max-width:440px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);">
                    <div style="width:48px;height:48px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;color:#34d399;font-size:24px;">
                        ✓
                    </div>
                    <h2 style="margin:0 0 8px;font-size:18px;color:#ffffff;">¡Canal de YouTube Conectado!</h2>
                    <p style="color:#a1a1aa;font-size:13px;line-height:1.5;margin-bottom:24px;">
                        Tu refresh_token ha sido guardado de forma segura en PostgreSQL. Ahora DASMO Office puede publicar Shorts automáticamente.
                    </p>
                    <a href="http://localhost:3000" style="display:inline-block;background:#4f46e5;color:white;padding:10px 20px;border-radius:10px;text-decoration:none;font-size:13px;font-weight:500;">
                        Volver al Dashboard
                    </a>
                    <script>
                        try {
                            window.opener?.postMessage({ type: 'YOUTUBE_AUTH_SUCCESS' }, '*');
                            setTimeout(() => { window.close(); }, 3500);
                        } catch (e) {}
                    </script>
                </div>
            </body>
        </html>
        """
    )
