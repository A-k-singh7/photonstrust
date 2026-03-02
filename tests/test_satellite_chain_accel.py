from __future__ import annotations

import pytest

import photonstrust.pipeline.satellite_chain_accel as accel_mod


def test_accumulate_key_bits_numpy_path_clips_negative_rates() -> None:
    value = accel_mod.accumulate_key_bits([100.0, -20.0, 50.0], 2.0, backend="numpy")
    assert value == pytest.approx(300.0)


def test_accumulate_key_bits_auto_falls_back_to_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"numpy": 0}

    monkeypatch.setattr(accel_mod, "jax_available", lambda: False)

    def _fake_numpy(key_rates_bps, dt_s):
        _ = key_rates_bps, dt_s
        calls["numpy"] += 1
        return 42.5

    def _fake_jax(key_rates_bps, dt_s):
        _ = key_rates_bps, dt_s
        raise AssertionError("JAX path should not be used when auto falls back to numpy")

    monkeypatch.setattr(accel_mod, "_accumulate_key_bits_numpy", _fake_numpy)
    monkeypatch.setattr(accel_mod, "_accumulate_key_bits_jax", _fake_jax)

    value = accel_mod.accumulate_key_bits([1.0, 2.0, 3.0], 1.0, backend="auto")
    assert value == pytest.approx(42.5)
    assert calls["numpy"] == 1

