"""The printable marker PDF: valid, to spec, and in sync with the committed copy."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from emberscan_workers.geometry.marker import MARKER_COLS, MARKER_ROWS, SQUARE_IN

WORKERS = Path(__file__).resolve().parents[1]
SCRIPT = WORKERS / "scripts" / "make_marker_pdf.py"
COMMITTED = WORKERS.parent / "docs" / "filming" / "emberscan-scale-marker.pdf"


def _generate(tmp_path: Path) -> bytes:
    out = tmp_path / "marker.pdf"
    subprocess.run([sys.executable, str(SCRIPT), str(out)], check=True, capture_output=True)
    return out.read_bytes()


def test_pdf_structure_and_squares(tmp_path: Path) -> None:
    pdf = _generate(tmp_path)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert b"/MediaBox [0 0 612 792]" in pdf
    # xref offsets point at their objects.
    xref = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    entries = re.findall(rb"(\d{10}) 00000 n ", pdf[xref:])
    for i, off in enumerate(entries, start=1):
        assert pdf[int(off) :].startswith(b"%d 0 obj" % i)
    # Exactly half the board's squares are black, each exactly SQUARE_IN (72 pt) wide.
    side = f"{SQUARE_IN * 72:.2f}".encode()
    squares = re.findall(rb"0\.000 0\.000 0\.000 rg [\d.]+ [\d.]+ " + side + b" " + side, pdf)
    assert len(squares) == MARKER_COLS * MARKER_ROWS // 2
    assert b"WALL EDGE" in pdf and b"Print at 100% / Actual size" in pdf


def test_committed_pdf_matches_generator(tmp_path: Path) -> None:
    """docs/filming/emberscan-scale-marker.pdf must be regenerated when the spec changes."""
    assert COMMITTED.read_bytes() == _generate(tmp_path)
