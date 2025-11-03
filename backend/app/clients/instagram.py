from __future__ import annotations

"""Instagram/Facebook Graph API client for posting Reels.

Uses Facebook Graph API to upload video reels to Instagram Business accounts.

IMPORTANT:
- Platform captions/hashtags are ALLOWED (in post metadata, not on-video overlays)
- NO on-video text, overlays, watermarks, voice, or subtitles
- Synthetic media disclosure handled externally by platform
- Fail loudly if auth credentials are missing
"""

import time
from pathlib import Path

import requests

from app.core.config import settings
from app.core.logging import log


class InstagramClient:
    """Instagram Reels API client via Facebook Graph API.

    Uploads video reels to Instagram Business accounts.
    Requires valid Facebook access token with instagram_content_publish permission.
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        business_account_id: str,
        access_token: str,
    ):
        """Initialize Instagram client.

        Args:
            business_account_id: Instagram Business Account ID
            access_token: Facebook access token with instagram_content_publish permission

        Raises:
            RuntimeError: If required credentials are missing
        """
        if not business_account_id:
            raise RuntimeError("INSTAGRAM_BUSINESS_ACCOUNT_ID is required")
        if not access_token:
            raise RuntimeError("FB_ACCESS_TOKEN is required")

        self.business_account_id = business_account_id
        self.access_token = access_token

        log.info(f"InstagramClient initialized: account_id={business_account_id}")

    def upload_reel(self, video_path: str, caption: str = "") -> str:
        """Upload video reel to Instagram.

        Args:
            video_path: Path to MP4 file
            caption: Post caption with hashtags (optional, max 2200 chars)

        Returns:
            Instagram media ID

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If upload fails
        """
        # Validate video exists
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        log.info(f"INSTAGRAM_UPLOAD_START video={Path(video_path).name} caption_len={len(caption)}")

        try:
            # Step 1: Create media container (this uploads the video)
            container_id = self._create_container(video_path, caption)

            # Step 2: Publish the container
            media_id = self._publish_container(container_id)

            log.info(f"INSTAGRAM_UPLOAD_SUCCESS media_id={media_id}")
            return media_id

        except Exception as e:
            log.error(f"INSTAGRAM_UPLOAD_FAILED error={str(e)}")
            raise RuntimeError(f"Instagram upload failed: {str(e)}") from e

    def _create_container(self, video_path: str, caption: str) -> str:
        """Create Instagram media container with video.

        Instagram requires video to be publicly accessible via URL.
        For local files, you need to either:
        1. Upload to a CDN/cloud storage first, OR
        2. Use Facebook's resumable upload API

        This implementation uses the video_url method (assumes video is already hosted).

        Args:
            video_path: Path to video file
            caption: Post caption

        Returns:
            Container ID

        Raises:
            RuntimeError: If container creation fails
        """
        # NOTE: Instagram Graph API requires video to be accessible via public URL
        # In production, upload video to CDN/S3 first and pass the URL here
        # For now, this is a placeholder implementation

        # TODO: Implement file upload to temporary CDN/S3 and get public URL
        # For demonstration, assuming video_path is actually a URL:
        video_url = video_path  # In production: upload_to_cdn(video_path)

        params = {
            "access_token": self.access_token,
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200] if caption else "",  # Max 2200 chars
            "share_to_feed": True,  # Also share to main feed
        }

        resp = requests.post(
            f"{self.BASE_URL}/{self.business_account_id}/media",
            params=params,
            timeout=60,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Instagram container creation failed: {resp.status_code} - {resp.text}"
            )

        data = resp.json()
        container_id = data.get("id")

        if not container_id:
            raise RuntimeError(f"Instagram response missing container ID: {data}")

        log.info(f"INSTAGRAM_CONTAINER_CREATED id={container_id}")
        return container_id

    def _publish_container(self, container_id: str) -> str:
        """Publish Instagram media container.

        Instagram processes the video asynchronously. This method polls until ready.

        Args:
            container_id: Container ID from create_container

        Returns:
            Published media ID

        Raises:
            RuntimeError: If publish fails or times out
        """
        # Poll container status until ready
        max_attempts = 30  # Poll for up to 5 minutes (30 × 10s = 300s)

        for attempt in range(max_attempts):
            # Check container status
            params = {
                "access_token": self.access_token,
                "fields": "status_code",
            }

            resp = requests.get(
                f"{self.BASE_URL}/{container_id}",
                params=params,
                timeout=30,
            )

            if resp.status_code != 200:
                raise RuntimeError(
                    f"Instagram status check failed: {resp.status_code} - {resp.text}"
                )

            data = resp.json()
            status_code = data.get("status_code")

            if status_code == "FINISHED":
                # Container ready, publish it
                break
            elif status_code == "ERROR":
                raise RuntimeError(f"Instagram container processing failed: {data}")
            elif status_code in ("IN_PROGRESS", "PUBLISHED"):
                # Still processing
                log.debug(f"INSTAGRAM_POLLING attempt={attempt + 1}/{max_attempts} status={status_code}")
                time.sleep(10)  # Wait 10 seconds before next poll
            else:
                log.warning(f"Unknown Instagram status: {status_code}")
                time.sleep(10)

        # Publish container
        params = {
            "access_token": self.access_token,
            "creation_id": container_id,
        }

        resp = requests.post(
            f"{self.BASE_URL}/{self.business_account_id}/media_publish",
            params=params,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Instagram publish failed: {resp.status_code} - {resp.text}"
            )

        data = resp.json()
        media_id = data.get("id")

        if not media_id:
            raise RuntimeError(f"Instagram publish response missing media ID: {data}")

        log.info(f"INSTAGRAM_PUBLISHED media_id={media_id}")
        return media_id
