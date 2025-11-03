from __future__ import annotations

"""TikTok Content Posting API client implementation.

Uses TikTok Content Posting API (Direct Post) to upload videos.

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


class TikTokClient:
    """TikTok Content Posting API client.

    Uploads videos using Direct Post method.
    Requires valid access token.
    """

    BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(
        self,
        client_key: str,
        client_secret: str,
        access_token: str,
    ):
        """Initialize TikTok client.

        Args:
            client_key: TikTok app client key
            client_secret: TikTok app client secret
            access_token: Valid user access token

        Raises:
            RuntimeError: If required credentials are missing
        """
        if not client_key:
            raise RuntimeError("TIKTOK_CLIENT_KEY is required")
        if not client_secret:
            raise RuntimeError("TIKTOK_CLIENT_SECRET is required")
        if not access_token:
            raise RuntimeError("TIKTOK_ACCESS_TOKEN is required")

        self.client_key = client_key
        self.client_secret = client_secret
        self.access_token = access_token

        log.info("TikTokClient initialized")

    def upload_video(self, video_path: str, caption: str = "") -> str:
        """Upload video to TikTok.

        Args:
            video_path: Path to MP4 file
            caption: Post caption with hashtags (optional)

        Returns:
            TikTok post ID

        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If upload fails
        """
        # Validate video exists
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        log.info(f"TIKTOK_UPLOAD_START video={Path(video_path).name} caption_len={len(caption)}")

        try:
            # Step 1: Initialize upload
            post_info = self._init_upload()

            # Step 2: Upload video bytes
            upload_url = post_info["upload_url"]
            self._upload_bytes(upload_url, video_path)

            # Step 3: Publish post
            post_id = self._publish_post(post_info["publish_id"], caption)

            log.info(f"TIKTOK_UPLOAD_SUCCESS post_id={post_id}")
            return post_id

        except Exception as e:
            log.error(f"TIKTOK_UPLOAD_FAILED error={str(e)}")
            raise RuntimeError(f"TikTok upload failed: {str(e)}") from e

    def _init_upload(self) -> dict:
        """Initialize direct post upload.

        Returns:
            Dict with upload_url and publish_id

        Raises:
            RuntimeError: If initialization fails
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "post_info": {
                "title": "",  # No title, caption only
                "privacy_level": "SELF_ONLY",  # Start as private (can change later)
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",  # Will use upload_url
            },
        }

        resp = requests.post(
            f"{self.BASE_URL}/post/publish/inbox/video/init/",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"TikTok init upload failed: {resp.status_code} - {resp.text}"
            )

        data = resp.json().get("data", {})

        if "upload_url" not in data or "publish_id" not in data:
            raise RuntimeError(f"TikTok init response missing fields: {data}")

        return {
            "upload_url": data["upload_url"],
            "publish_id": data["publish_id"],
        }

    def _upload_bytes(self, upload_url: str, video_path: str) -> None:
        """Upload video bytes to TikTok's upload URL.

        Args:
            upload_url: Pre-signed upload URL from init
            video_path: Path to video file

        Raises:
            RuntimeError: If upload fails
        """
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
        }

        resp = requests.put(
            upload_url,
            headers=headers,
            data=video_bytes,
            timeout=180,  # 3 minute timeout for upload
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"TikTok video upload failed: {resp.status_code} - {resp.text}"
            )

        log.info(f"TIKTOK_BYTES_UPLOADED size={len(video_bytes)} bytes")

    def _publish_post(self, publish_id: str, caption: str) -> str:
        """Publish the uploaded video as a post.

        Args:
            publish_id: ID from init upload
            caption: Post caption (with hashtags if provided)

        Returns:
            TikTok post ID

        Raises:
            RuntimeError: If publish fails
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "publish_id": publish_id,
            "post_info": {
                "title": caption[:150] if caption else "",  # Max 150 chars
            },
        }

        resp = requests.post(
            f"{self.BASE_URL}/post/publish/",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"TikTok publish failed: {resp.status_code} - {resp.text}"
            )

        data = resp.json().get("data", {})
        post_id = data.get("post_id")

        if not post_id:
            raise RuntimeError(f"TikTok publish response missing post_id: {data}")

        return post_id
