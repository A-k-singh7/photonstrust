"""Tests for Phase D CLI subcommands (list, info, demo, quickstart)."""

from __future__ import annotations

import sys

import pytest


def _run_cli_captured(monkeypatch, capsys, *args):
    """Run photonstrust CLI main() with given args, capture output."""
    monkeypatch.setattr(sys, "argv", ["photonstrust"] + list(args))
    from photonstrust.cli import main

    try:
        main()
    except SystemExit:
        pass
    return capsys.readouterr()


# ---- list subcommand -------------------------------------------------------


def test_list_protocols_contains_bb84_decoy(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "protocols")
    assert "bb84_decoy" in out.out


def test_list_protocols_contains_bbm92(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "protocols")
    assert "bbm92" in out.out


def test_list_bands_contains_c_1550(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "bands")
    assert "c_1550" in out.out


def test_list_detectors_contains_snspd(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "detectors")
    assert "snspd" in out.out


def test_list_scenarios_contains_bb84_metro(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "scenarios")
    assert "bb84_metro" in out.out


def test_list_channels_contains_fiber(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "channels")
    assert "fiber" in out.out


def test_list_pdks(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "list", "pdks")
    # Should show at least the table header or a PDK name
    assert "Name" in out.out or "pdk" in out.out.lower()


# ---- info subcommand -------------------------------------------------------


def test_info_bb84(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "info", "bb84")
    assert "bb84_decoy" in out.out or "Protocol" in out.out


def test_info_snspd(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "info", "snspd")
    assert "snspd" in out.out
    assert "Detector" in out.out or "PDE" in out.out


# ---- demo subcommand -------------------------------------------------------


def test_demo_no_args_lists_scenarios(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "demo")
    assert "bb84_metro" in out.out


# ---- quickstart subcommand -------------------------------------------------


def test_quickstart_non_interactive(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "quickstart", "--non-interactive")
    combined = out.out + out.err
    # Should contain some result output (protocol name or key rate info)
    assert "bb84" in combined.lower() or "key rate" in combined.lower() or "Protocol" in combined


def test_quickstart_help(monkeypatch, capsys):
    out = _run_cli_captured(monkeypatch, capsys, "quickstart", "--help")
    combined = out.out + out.err
    assert "wizard" in combined.lower() or "quickstart" in combined.lower()
