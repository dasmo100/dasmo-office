import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.dynamic_settings import get_active_config

logger = logging.getLogger(__name__)


class YouTubePublisherAgent(BaseAgent):
    """Publishes rendered vertical video shorts to YouTube Data API v3
    using OAuth 2.0 refresh tokens, setting privacy, synthetic media flags,
    and video metadata.
    """

    def __init__(self) -> None:
        super().__init__(name="youtube_publisher")

    async def run(
        self,
        input_data: Dict[str, Any],
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Upload a rendered video to YouTube.

        Args:
            input_data: Dictionary containing:
                - short_id (int)
                - video_path (str)
                - title (str, optional)
                - description (str, optional)
                - tags (list[str], optional)
                - category_id (str, optional, default "28")
                - privacy_status (str, optional: "private", "unlisted", "public")
        """
        short_id = input_data.get("short_id")
        video_path = input_data.get("video_path")
        title = input_data.get("title", f"Short #{short_id}")
        description = input_data.get("description", "#Shorts #AI")
        tags = input_data.get("tags") or ["Shorts", "AI"]
        category_id = str(input_data.get("category_id", "28"))
        privacy_status = input_data.get("privacy_status", "private")

        if not video_path or not Path(video_path).exists():
            raise FileNotFoundError(f"Rendered video file not found at '{video_path}'")

        # Resolve active YouTube OAuth configuration
        config = await get_active_config(db_session)
        client_id = settings.YOUTUBE_CLIENT_ID
        client_secret = settings.YOUTUBE_CLIENT_SECRET
        refresh_token = config.youtube_refresh_token or settings.YOUTUBE_REFRESH_TOKEN

        if not refresh_token:
            raise ValueError(
                "YouTube refresh token not configured. Please add your YOUTUBE_REFRESH_TOKEN "
                "in Settings from the Web Dashboard or in your .env file."
            )

        if not client_id or not client_secret:
            raise ValueError(
                "YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are required in environment (.env) "
                "to authenticate with the YouTube Data API."
            )

        self.logger.info("Initializing YouTube Data API client with OAuth refresh token...")

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        youtube = build("youtube", "v3", credentials=creds)

        snippet = {
            "title": title[:100],
            "description": description,
            "tags": tags[:15] if isinstance(tags, list) else [],
            "categoryId": category_id,
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        }

        status = {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # YouTube synthetic / AI content disclosure
        }

        body = {
            "snippet": snippet,
            "status": status,
        }

        self.logger.info(
            "Uploading Short '%s' (%s) to YouTube with privacy '%s'...",
            title[:40],
            video_path,
            privacy_status,
        )

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 4,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = request.execute()
        video_id = response.get("id")

        self.logger.info(
            "Successfully uploaded Short #%s to YouTube! Video ID: %s (https://youtu.be/%s)",
            short_id,
            video_id,
            video_id,
        )

        return {
            "status": "success",
            "agent": self.name,
            "short_id": short_id,
            "youtube_video_id": video_id,
            "youtube_url": f"https://youtu.be/{video_id}",
            "privacy_status": privacy_status,
        }
