"""
Focused tests for security, reliability, and input validation improvements.
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.models import SystemTaskPayload
from agents.base import AuditTrail, PHIGuard, SecurityException


class TestInputValidation:
    """Tests for metric validation (NaN, Inf rejection)."""

    def test_reject_nan_primary_metric(self):
        with pytest.raises(ValueError, match="finite"):
            SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=float("nan"))

    def test_reject_nan_secondary_metric(self):
        with pytest.raises(ValueError, match="finite"):
            SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=10.0, secondary_metric=float("nan"))

    def test_reject_inf_primary_metric(self):
        with pytest.raises(ValueError, match="finite"):
            SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=float("inf"))

    def test_reject_negative_inf(self):
        with pytest.raises(ValueError, match="finite"):
            SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=float("-inf"))

    def test_accept_valid_metrics(self):
        p = SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=10.0, secondary_metric=5.0)
        assert p.primary_metric == 10.0
        assert p.secondary_metric == 5.0

    def test_accept_zero_metrics(self):
        p = SystemTaskPayload(task_id="T1", target_identifier="K1", primary_metric=0.0, secondary_metric=0.0)
        assert p.primary_metric == 0.0

    def test_reject_empty_task_id(self):
        with pytest.raises(ValueError):
            SystemTaskPayload(task_id="", target_identifier="K1", primary_metric=10.0)

    def test_reject_empty_target(self):
        with pytest.raises(ValueError):
            SystemTaskPayload(task_id="T1", target_identifier="", primary_metric=10.0)


class TestAuditTrailSecurity:
    """Tests for HMAC audit trail security improvements."""

    def test_audit_trail_with_custom_key(self):
        trail = AuditTrail(secret_key="test-key-123")
        entry = trail.log("actor1", "tier1", "TEST_EVENT", {"data": "value"})
        assert "current_hash" in entry
        assert entry["prev_hash"] == "GENESIS_BLOCK_0000000000000000"

    def test_audit_trail_chain_integrity(self):
        trail = AuditTrail(secret_key="test-key-456")
        trail.log("actor1", "tier1", "EVENT_1", {"step": 1})
        trail.log("actor2", "tier1", "EVENT_2", {"step": 2})
        trail.log("actor3", "tier1", "EVENT_3", {"step": 3})
        assert trail.verify_integrity() is True

    def test_audit_trail_tamper_detection(self):
        trail = AuditTrail(secret_key="test-key-789")
        trail.log("actor1", "tier1", "EVENT_1", {"step": 1})
        trail.log("actor2", "tier1", "EVENT_2", {"step": 2})
        # Tamper with the chain
        trail.logs[0]["current_hash"] = "TAMPERED_HASH"
        assert trail.verify_integrity() is False


class TestPHIGuardRedaction:
    """Tests for PHI guard redaction functionality."""

    def test_redact_phi_email(self):
        text = "Contact user@example.com for details"
        redacted = PHIGuard.redact_phi(text)
        assert "[REDACTED_IDENTIFIER]" in redacted
        assert "user@example.com" not in redacted

    def test_redact_phi_ssn(self):
        text = "SSN: 123-45-6789"
        redacted = PHIGuard.redact_phi(text)
        assert "[REDACTED_IDENTIFIER]" in redacted

    def test_redact_phi_mrn(self):
        text = "Patient MRN-12345678"
        redacted = PHIGuard.redact_phi(text)
        assert "[REDACTED_IDENTIFIER]" in redacted

    def test_clean_text_unchanged(self):
        text = "Normal specimen KEY-001 within parameters"
        assert PHIGuard.redact_phi(text) == text


class TestCLIBatchErrorHandling:
    """Tests for CLI batch command error handling."""

    def test_batch_missing_file(self, tmp_path, capsys):
        from cli import main
        result = main(["batch", "-i", str(tmp_path / "nonexistent.csv")])
        assert result == 1

    def test_batch_malformed_csv(self, tmp_path, capsys):
        from cli import main
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("invalid,csv\nunclosed\"quote\n")
        result = main(["batch", "-i", str(bad_csv), "-o", str(tmp_path / "out.csv")])
        # Should handle gracefully (either skip or error gracefully)
        assert result in (0, 1)

    def test_batch_with_invalid_rows(self, tmp_path, capsys):
        from cli import main
        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text(
            "task_id,target_identifier,primary_metric,secondary_metric\n"
            "T1,K1,10.0,5.0\n"
            "T2,K2,invalid,3.0\n"
            "T3,K3,15.0,7.0\n"
        )
        out_file = tmp_path / "out.csv"
        result = main(["batch", "-i", str(csv_file), "-o", str(out_file)])
        assert result == 0
        assert out_file.exists()
