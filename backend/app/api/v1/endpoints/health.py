from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", status_code=200)
async def check_health() -> Dict[str, Any]:
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "healthy",
        "service": "dasmo-api",
        "version": "0.1.0",
    }
