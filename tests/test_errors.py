"""Tests for the photonstrust.errors smart error module."""

from __future__ import annotations

import pytest

from photonstrust.errors import (
    ConfigError,
    DependencyError,
    NetworkError,
    PhysicsError,
    PhotonsTrustError,
    ProtocolError,
    ValidationError,
    suggest_fix,
)


# ------------------------------------------------------------------
# PhotonsTrustError formatting
# ------------------------------------------------------------------


class TestPhotosTrustErrorFormatting:
    def test_str_includes_suggestion(self):
        err = PhotonsTrustError("something broke", suggestion="try rebooting")
        text = str(err)
        assert "something broke" in text
        assert "Suggestion: try rebooting" in text

    def test_str_includes_doc_link(self):
        err = PhotonsTrustError(
            "bad config",
            doc_link="https://docs.example.com/config",
        )
        text = str(err)
        assert "bad config" in text
        assert "See: https://docs.example.com/config" in text

    def test_str_plain_when_no_extras(self):
        err = PhotonsTrustError("plain error")
        assert str(err) == "plain error"


# ------------------------------------------------------------------
# Backward-compatibility (stdlib exception subclassing)
# ------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_config_error_is_value_error(self):
        err = ConfigError("bad value")
        assert isinstance(err, ValueError)
        assert isinstance(err, PhotonsTrustError)

    def test_physics_error_is_runtime_error(self):
        err = PhysicsError("constraint violated")
        assert isinstance(err, RuntimeError)
        assert isinstance(err, PhotonsTrustError)

    def test_dependency_error_is_import_error(self):
        err = DependencyError("missing jax")
        assert isinstance(err, ImportError)
        assert isinstance(err, PhotonsTrustError)

    def test_protocol_error_is_value_error(self):
        err = ProtocolError("unknown protocol")
        assert isinstance(err, ValueError)
        assert isinstance(err, PhotonsTrustError)


# ------------------------------------------------------------------
# suggest_fix() catalog matching
# ------------------------------------------------------------------


class TestSuggestFix:
    def test_matches_unknown_protocol(self):
        err = ValueError("Unsupported QKD protocol name: 'foo'")
        suggestion = suggest_fix(err)
        assert "protocol" in suggestion.lower() or "Available protocols" in suggestion

    def test_matches_unknown_band(self):
        err = ValueError("Unknown band 'x_band'")
        suggestion = suggest_fix(err)
        assert "band" in suggestion.lower() or "Available bands" in suggestion

    def test_matches_negative_value(self):
        err = RuntimeError("negative loss detected")
        suggestion = suggest_fix(err)
        assert suggestion  # non-empty
        assert "non-negative" in suggestion.lower() or "must be" in suggestion.lower()

    def test_returns_empty_for_unknown_error(self):
        err = Exception("completely novel error xyz123")
        suggestion = suggest_fix(err)
        assert suggestion == ""


# ------------------------------------------------------------------
# Integration: ProtocolError from registry.py
# ------------------------------------------------------------------


class TestRegistryProtocolError:
    def test_invalid_protocol_raises_protocol_error_with_names(self):
        from photonstrust.qkd_protocols.registry import resolve_protocol_module

        with pytest.raises(ProtocolError, match="Unsupported QKD protocol") as exc_info:
            resolve_protocol_module("nonexistent_protocol_xyz")
        text = str(exc_info.value)
        # Should list available protocol names
        assert "bb84_decoy" in text
        assert "bbm92" in text

        # Backward compat: also caught by ValueError
        with pytest.raises(ValueError):
            resolve_protocol_module("nonexistent_protocol_xyz")


# ------------------------------------------------------------------
# Integration: ConfigError from presets.py
# ------------------------------------------------------------------


class TestPresetsConfigError:
    def test_unknown_band_raises_config_error_with_bands(self):
        from photonstrust.presets import get_band_preset

        with pytest.raises(ConfigError, match="Unknown band") as exc_info:
            get_band_preset("invalid_band_xyz")
        text = str(exc_info.value)
        assert "c_1550" in text
        assert "nir_795" in text

        # Backward compat
        with pytest.raises(ValueError):
            get_band_preset("invalid_band_xyz")

    def test_unknown_detector_raises_config_error_with_detectors(self):
        from photonstrust.presets import get_detector_preset

        with pytest.raises(ConfigError, match="Unknown detector") as exc_info:
            get_detector_preset("invalid_detector_xyz")
        text = str(exc_info.value)
        assert "snspd" in text
        assert "ingaas" in text

        # Backward compat
        with pytest.raises(ValueError):
            get_detector_preset("invalid_detector_xyz")


# ------------------------------------------------------------------
# Integration: ConfigError from config._expand_distance()
# ------------------------------------------------------------------


class TestConfigExpandDistanceError:
    def test_step_zero_raises_config_error(self):
        from photonstrust.config import _expand_distance

        with pytest.raises(ConfigError, match="step must be > 0") as exc_info:
            _expand_distance({"start": 0, "stop": 100, "step": 0})
        text = str(exc_info.value)
        assert "Suggestion" in text

        # Backward compat
        with pytest.raises(ValueError):
            _expand_distance({"start": 0, "stop": 100, "step": 0})
