"""Tests for scheduler posting logic and idempotency."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.scheduler import run_posting_cycle


class TestSchedulerIdempotency:
    """Tests for scheduler idempotency and multi-platform posting."""

    def test_scheduler_idempotency_prevents_repost(self):
        """Verify scheduler doesn't re-post to platforms already posted."""
        # Create temp videos.json with a video that's already posted to Instagram
        with tempfile.TemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            test_videos_path = f.name
            videos_data = [
                {
                    "id": "test-video-001",
                    "status": "approved",
                    "video_path": "app/data/generated/videos/test-video-001.mp4",
                    "social": {
                        "title": "Test Fitness Video",
                        "hashtags": ["#fitness", "#workout"],
                    },
                    "posted_platforms": {
                        "instagram": {
                            "post_id": "123456789",
                            "posted_at": "2025-01-01T10:00:00Z",
                        }
                    },
                }
            ]
            json.dump(videos_data, f)
            f.flush()

        try:
            # Mock posting window to return True
            with patch("app.core.scheduler._in_posting_window", return_value=True):
                # Mock the storage functions
                with patch("app.core.scheduler.read_json", return_value=videos_data):
                    with patch("app.core.scheduler.update_json_item") as mock_update:
                        # Mock TikTok client (should be called since not yet posted to TikTok)
                        with patch("app.core.scheduler._post_to_tiktok", return_value="tiktok_post_123") as mock_tiktok:
                            # Mock Instagram client (should NOT be called - already posted)
                            with patch("app.core.scheduler._post_to_instagram") as mock_instagram:
                                # Run posting cycle
                                result = run_posting_cycle()

                                # Verify Instagram was NOT called (already posted)
                                mock_instagram.assert_not_called()

                                # Verify TikTok WAS called (not yet posted)
                                mock_tiktok.assert_called_once()

                                # Verify result indicates success
                                assert result["ok"] is True
                                assert result["posted"] == 1  # Only TikTok posted
                                assert "tiktok" in result["platforms"]
                                assert "instagram" not in result["platforms"]

        finally:
            # Cleanup
            Path(test_videos_path).unlink(missing_ok=True)

    def test_scheduler_respects_tiktok_delay(self):
        """Verify scheduler waits 90 minutes after Instagram before posting to TikTok."""
        # Create video posted to Instagram less than 90 minutes ago
        recent_instagram_post = datetime.utcnow().isoformat() + "Z"

        with tempfile.TemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            test_videos_path = f.name
            videos_data = [
                {
                    "id": "test-video-002",
                    "status": "approved",
                    "video_path": "app/data/generated/videos/test-video-002.mp4",
                    "social": {
                        "title": "Test Video",
                        "hashtags": ["#fitness"],
                    },
                    "posted_platforms": {
                        "instagram": {
                            "post_id": "insta_123",
                            "posted_at": recent_instagram_post,  # Just now
                        }
                    },
                }
            ]
            json.dump(videos_data, f)
            f.flush()

        try:
            with patch("app.core.scheduler._in_posting_window", return_value=True):
                with patch("app.core.scheduler.read_json", return_value=videos_data):
                    with patch("app.core.scheduler.update_json_item"):
                        with patch("app.core.scheduler._post_to_tiktok") as mock_tiktok:
                            # Run posting cycle
                            result = run_posting_cycle()

                            # Verify TikTok was NOT called (delay not met)
                            mock_tiktok.assert_not_called()

                            # Verify result indicates no posts made
                            assert result["ok"] is True
                            assert result["posted"] == 0

        finally:
            Path(test_videos_path).unlink(missing_ok=True)

    def test_scheduler_posts_to_instagram_first_only(self):
        """Verify scheduler posts to Instagram first, TikTok must wait for next cycle."""
        with tempfile.TemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            test_videos_path = f.name
            videos_data = [
                {
                    "id": "test-video-003",
                    "status": "approved",
                    "video_path": "app/data/generated/videos/test-video-003.mp4",
                    "social": {
                        "title": "Fresh Video",
                        "hashtags": ["#test"],
                    },
                    "posted_platforms": {},  # No platforms posted yet
                }
            ]
            json.dump(videos_data, f)
            f.flush()

        try:
            with patch("app.core.scheduler._in_posting_window", return_value=True):
                with patch("app.core.scheduler.read_json", return_value=videos_data):
                    with patch("app.core.scheduler.update_json_item"):
                        with patch("app.core.scheduler._post_to_instagram", return_value="insta_456") as mock_instagram:
                            with patch("app.core.scheduler._post_to_tiktok") as mock_tiktok:
                                # Run posting cycle
                                result = run_posting_cycle()

                                # Verify Instagram was called first
                                mock_instagram.assert_called_once()

                                # TikTok should NOT be called - delay not met (just posted to Instagram)
                                mock_tiktok.assert_not_called()

                                # Verify only Instagram posted
                                assert result["ok"] is True
                                assert result["posted"] == 1
                                assert result["platforms"] == ["instagram"]

        finally:
            Path(test_videos_path).unlink(missing_ok=True)
