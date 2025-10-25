from __future__ import annotations

import os
import tempfile
from decimal import Decimal

import pytest

from app.core import cost, ids, storage


class TestCostAccuracy:
    """Tests for Decimal-based cost tracking (P0-1)."""

    def test_decimal_precision(self):
        """Verify cost uses Decimal, not float."""
        cost.reset_cycle()
        assert isinstance(cost.get_current_cost(), Decimal)

    def test_budget_cap_enforced(self):
        """Verify budget cap prevents overspend."""
        from app.core.config import settings

        cost.reset_cycle()
        original_max = settings.max_cost_per_run
        settings.max_cost_per_run = Decimal("0.10")

        try:
            # Should succeed
            cost.add_cost(Decimal("0.05"), "test1")
            assert cost.get_current_cost() == Decimal("0.05")

            # Should fail (0.05 + 0.10 = 0.15 > 0.10)
            with pytest.raises(RuntimeError, match="Budget exceeded"):
                cost.add_cost(Decimal("0.10"), "test2")

        finally:
            settings.max_cost_per_run = original_max
            cost.reset_cycle()

    def test_no_float_drift(self):
        """Verify repeated additions don't drift."""
        cost.reset_cycle()
        for _ in range(100):
            cost.add_cost(Decimal("0.001"), "micro")
        assert cost.get_current_cost() == Decimal("0.1")


class TestPathTraversal:
    """Tests for path traversal protection (P0-2)."""

    def test_safe_join_blocks_traversal(self):
        """Verify safe_join rejects .. components."""
        with pytest.raises(ValueError, match="Path traversal blocked"):
            storage.safe_join("app", "data", "..", "etc", "passwd")

    def test_safe_join_allows_normal_paths(self):
        """Verify safe_join allows legitimate paths."""
        path = storage.safe_join("app", "data", "generated", "video.mp4")
        assert "generated" in path
        assert ".." not in path

    def test_indexer_rejects_malicious_id(self):
        """Verify indexer rejects IDs with path traversal."""
        from app.agents import indexer

        # Create a temp file to index
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_path = f.name

        try:
            payload = {"id": "../../../etc/passwd", "seed": 123}
            with pytest.raises(ValueError, match="Path traversal blocked"):
                indexer.index(temp_path, payload)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestSchemaValidation:
    """Tests for JSON schema validation (P1-8)."""

    def test_append_with_valid_schema(self):
        """Verify valid items pass schema validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_path = f.name
            f.write("[]")

        try:
            item = {"id": "test", "path": "/foo", "status": "generated", "ts": 123}
            schema = {"required": ["id", "path", "status", "ts"]}
            storage.append_json_line(test_path, item, schema=schema)

            data = storage.read_json(test_path)
            assert len(data) == 1
            assert data[0]["id"] == "test"
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    def test_append_with_invalid_schema(self):
        """Verify missing required fields raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_path = f.name
            f.write("[]")

        try:
            item = {"id": "test"}  # Missing required fields
            schema = {"required": ["id", "path", "status"]}

            with pytest.raises(ValueError, match="missing required key"):
                storage.append_json_line(test_path, item, schema=schema)
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)


class TestDeterministicIDs:
    """Tests for deterministic ID generation (P1-9)."""

    def test_same_payload_same_id(self):
        """Verify identical payloads produce identical IDs."""
        payload = {"base": "prompt", "neg": "negative", "seed": 12345}
        id1 = ids.deterministic_id(payload)
        id2 = ids.deterministic_id(payload)
        assert id1 == id2

    def test_different_seed_different_id(self):
        """Verify different seeds produce different IDs."""
        payload1 = {"base": "prompt", "neg": "negative", "seed": 11111}
        payload2 = {"base": "prompt", "neg": "negative", "seed": 22222}
        id1 = ids.deterministic_id(payload1)
        id2 = ids.deterministic_id(payload2)
        assert id1 != id2

    def test_id_is_hex(self):
        """Verify ID is hex string (alphanumeric)."""
        payload = {"base": "test", "neg": "", "seed": 1}
        vid_id = ids.deterministic_id(payload)
        assert len(vid_id) == 16
        assert all(c in "0123456789abcdef" for c in vid_id)


class TestSecretHandling:
    """Tests for secret handling (P0-6)."""

    def test_healthz_no_secrets(self):
        """Verify /healthz doesn't expose API keys."""
        from app.api.routes import healthz

        response = healthz()
        assert "ok" in response
        assert "providers" in response
        # Should show status, not actual keys
        for provider, status in response["providers"].items():
            assert status in ["configured", "key_missing"]
            assert "API" not in status
            assert "key" not in status or status == "key_missing"
