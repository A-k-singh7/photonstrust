"""Tests for photonstrust.reporting.html_report."""

import re

import pytest

from photonstrust.reporting.html_report import (
    generate_html_report,
    generate_summary_card,
    _figure_to_base64,
    _render_table,
    _default_css,
)


# ---------------------------------------------------------------------------
# Mock result objects (avoid importing heavy simulation modules)
# ---------------------------------------------------------------------------


class _MockQKDResult:
    def __init__(
        self,
        distance_km=10,
        key_rate_bps=1000,
        qber_total=0.03,
        fidelity=0.97,
        loss_db=2.0,
        protocol_name="bb84",
    ):
        self.distance_km = distance_km
        self.key_rate_bps = key_rate_bps
        self.qber_total = qber_total
        self.fidelity = fidelity
        self.loss_db = loss_db
        self.protocol_name = protocol_name


class _MockQKDLinkResult:
    __name__ = "QKDLinkResult"

    def __init__(self):
        self.results = [
            _MockQKDResult(d, max(0, 5000 - 100 * d), 0.03 + 0.001 * d, 0.97 - 0.001 * d, 0.2 * d)
            for d in range(0, 60, 10)
        ]
        self.config = {"protocol": "bb84", "band": "c_1550"}

    def summary(self):
        return "BB84 link analysis\nMax distance: 50 km"

    def as_dict(self):
        return {"results": [vars(r) for r in self.results], "config": self.config}

    def max_distance_km(self):
        positive = [r.distance_km for r in self.results if r.key_rate_bps > 0]
        return max(positive) if positive else 0.0


# Override class name so _detect_result_type sees "QKDLinkResult"
_MockQKDLinkResult.__name__ = "QKDLinkResult"


class _MockProtocolComparison:
    def __init__(self):
        link_bb84 = _MockQKDLinkResult()
        link_tf = _MockQKDLinkResult()
        for r in link_tf.results:
            r.protocol_name = "tf_qkd"
            r.key_rate_bps = max(0, r.key_rate_bps * 1.5)
        link_tf.config = {"protocol": "tf_qkd", "band": "c_1550"}
        self.protocols = {"bb84": link_bb84, "tf_qkd": link_tf}

    def summary(self):
        return "Protocol comparison: bb84, tf_qkd"

    def winner_at(self, distance_km):
        return "tf_qkd"


_MockProtocolComparison.__name__ = "ProtocolComparison"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateHtmlReport:
    """Tests for generate_html_report."""

    def test_produces_html(self):
        """generate_html_report produces string containing <html>."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link)
        assert "<html" in html
        assert "</html>" in html
        assert "<!DOCTYPE html>" in html

    def test_contains_title(self):
        """Report contains the title string."""
        link = _MockQKDLinkResult()
        title = "My Custom BB84 Report"
        html = generate_html_report(link, title=title)
        assert title in html

    def test_contains_tables(self):
        """Report contains <table> elements."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link)
        assert "<table>" in html
        assert "</table>" in html

    def test_plots_included_by_default(self):
        """With include_plots=True, report contains base64 data URIs."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link, include_plots=True)
        assert "data:image/png;base64," in html

    def test_plots_excluded(self):
        """With include_plots=False, report does NOT contain base64 images."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link, include_plots=False)
        assert "data:image/png;base64," not in html

    def test_methodology_included(self):
        """With include_methodology=True, report contains methodology text."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link, include_methodology=True)
        assert "Methodology" in html or "methodology" in html

    def test_summary_card_shorter(self):
        """generate_summary_card is shorter than full report."""
        link = _MockQKDLinkResult()
        full = generate_html_report(link)
        card = generate_summary_card(link, title="Summary")
        assert len(card) < len(full)


class TestRenderTable:
    """Tests for _render_table."""

    def test_correct_structure(self):
        """_render_table produces valid HTML table with correct number of rows."""
        headers = ["A", "B", "C"]
        rows = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        html = _render_table(headers, rows, caption="Test")
        assert "<table>" in html
        assert "</table>" in html
        # 3 header cells
        assert html.count("<th>") == 3
        # 3 data rows * 3 cells = 9 <td> tags
        assert html.count("<td>") == 9
        # 3 <tr> in tbody
        assert html.count("<tr>") == 4  # 1 header + 3 data rows
        assert "Test" in html


class TestFigureToBase64:
    """Tests for _figure_to_base64."""

    def test_returns_data_uri(self):
        """_figure_to_base64 returns string starting with data:image/png;base64."""
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        result = _figure_to_base64(fig)
        plt.close(fig)
        assert result.startswith("data:image/png;base64,")
        # Verify base64 content is non-trivial
        b64_part = result.split(",", 1)[1]
        assert len(b64_part) > 100


class TestSelfContained:
    """Test that the report is self-contained."""

    def test_no_external_resources(self):
        """Report has no http:// or https:// external resource links
        (except in references section text)."""
        link = _MockQKDLinkResult()
        html = generate_html_report(link, include_plots=False)

        # Remove the references section before checking
        # References legitimately contain DOI URLs
        ref_pattern = re.compile(
            r'<section class="references">.*?</section>', re.DOTALL
        )
        html_no_refs = ref_pattern.sub("", html)

        assert "http://" not in html_no_refs
        assert "https://" not in html_no_refs


class TestProtocolComparison:
    """Test ProtocolComparison report generation."""

    def test_multiple_protocols(self):
        """ProtocolComparison mock generates report with multiple protocol names."""
        comp = _MockProtocolComparison()
        html = generate_html_report(comp)
        assert "bb84" in html
        assert "tf_qkd" in html
        assert "<html" in html

    def test_comparison_has_plots(self):
        """ProtocolComparison report includes plots by default."""
        comp = _MockProtocolComparison()
        html = generate_html_report(comp, include_plots=True)
        assert "data:image/png;base64," in html


class TestDefaultCss:
    """Tests for _default_css."""

    def test_css_contains_key_rules(self):
        """CSS contains key styling rules."""
        css = _default_css()
        assert "#1f77b4" in css  # primary color
        assert "@media print" in css
        assert ".metric-card" in css
        assert "font-family" in css
