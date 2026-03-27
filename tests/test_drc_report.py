"""Tests for DRC report rendering."""
import pytest
from photonstrust.chipverify.drc_report import render_drc_report

SAMPLE_DRC_PASS = {
    "violations": [],
    "summary": {"total_checks": 10},
    "pass": True,
}

SAMPLE_DRC_FAIL = {
    "violations": [
        {"rule": "MIN_WIDTH", "severity": "error", "message": "Width 350nm < 400nm min", "location": "wg1"},
        {"rule": "MIN_GAP", "severity": "warning", "message": "Gap 180nm < 200nm min", "location": "mmi1"},
        {"rule": "BEND_RADIUS", "severity": "info", "message": "Bend radius 4um close to limit", "location": "bend1"},
    ],
    "summary": {"total_checks": 15},
    "pass": False,
}


def test_text_pass():
    report = render_drc_report(SAMPLE_DRC_PASS, format="text")
    assert "PASS" in report
    assert "No violations" in report

def test_text_fail():
    report = render_drc_report(SAMPLE_DRC_FAIL, format="text")
    assert "FAIL" in report
    assert "MIN_WIDTH" in report
    assert "ERROR" in report

def test_markdown_format():
    report = render_drc_report(SAMPLE_DRC_FAIL, format="markdown")
    assert "# DRC Report" in report
    assert "| Rule |" in report
    assert "MIN_WIDTH" in report

def test_html_format():
    report = render_drc_report(SAMPLE_DRC_FAIL, format="html")
    assert "<h1" in report
    assert "<table" in report
    assert "MIN_WIDTH" in report

def test_violation_grouping():
    report = render_drc_report(SAMPLE_DRC_FAIL, format="text")
    assert "ERROR" in report
    assert "WARNING" in report
    assert "INFO" in report

def test_empty_violations():
    drc = {"violations": [], "summary": {}, "pass": True}
    report = render_drc_report(drc, format="text")
    assert "PASS" in report
