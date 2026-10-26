"""Write docs/filming/emberscan-scale-marker.pdf: the printable scale marker (story C5).

One US Letter page, pure vector, no dependencies: the PDF objects are written by hand. The
checkerboard geometry comes from emberscan_workers.geometry.marker, so the paper and the
detector share one spec. Output is deterministic (no timestamps), so it diffs cleanly.

Usage: python scripts/make_marker_pdf.py [output.pdf]
"""

from __future__ import annotations

import sys
from pathlib import Path

from emberscan_workers.geometry.marker import (
    BOARD_LEFT_IN,
    BOARD_TOP_IN,
    MARKER_COLS,
    MARKER_ROWS,
    MIN_PAGE_MARGIN_IN,
    PAGE_H_IN,
    PAGE_W_IN,
    SQUARE_IN,
    WALL_EDGE,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "filming" / "emberscan-scale-marker.pdf"
PT = 72.0  # points per inch
ORANGE = (1.0, 0.42, 0.0)
RULER_IN = 4.0

assert WALL_EDGE == "top", "layout below assumes the wall edge is the page's top short edge"


def _x(x_in: float) -> float:
    return x_in * PT


def _y(y_in: float) -> float:
    """Page y measured down from the top edge (inches) -> PDF y up from the bottom (pt)."""
    return (PAGE_H_IN - y_in) * PT


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Page:
    """Collects PDF content-stream operators in top-left inch coordinates."""

    def __init__(self) -> None:
        self.ops: list[str] = []
        self.extent = [PAGE_W_IN, PAGE_H_IN, 0.0, 0.0]  # min x, min y, max x, max y (in)

    def _touch(self, x0: float, y0: float, x1: float, y1: float) -> None:
        e = self.extent
        e[0], e[1] = min(e[0], x0, x1), min(e[1], y0, y1)
        e[2], e[3] = max(e[2], x0, x1), max(e[3], y0, y1)

    def rect(self, x: float, y: float, w: float, h: float, rgb: tuple[float, ...]) -> None:
        """Filled rectangle, top-left (x, y) and size in inches."""
        self._touch(x, y, x + w, y + h)
        r, g, b = rgb
        self.ops.append(
            f"{r:.3f} {g:.3f} {b:.3f} rg {_x(x):.2f} {_y(y + h):.2f} {w * PT:.2f} {h * PT:.2f} re f"
        )

    def line(self, x0: float, y0: float, x1: float, y1: float, width_pt: float = 1.0) -> None:
        self._touch(x0, y0, x1, y1)
        self.ops.append(
            f"0 0 0 RG {width_pt:.2f} w {_x(x0):.2f} {_y(y0):.2f} m {_x(x1):.2f} {_y(y1):.2f} l S"
        )

    def text(
        self,
        x: float,
        baseline: float,
        s: str,
        size: float,
        bold: bool = False,
        rgb: tuple[float, ...] = (0, 0, 0),
    ) -> None:
        """Left-aligned text; extent check uses a generous 0.6 em average glyph width."""
        self._touch(x, baseline - size * 0.75 / PT, x + len(s) * size * 0.6 / PT, baseline)
        font = "F2" if bold else "F1"
        r, g, b = rgb
        self.ops.append(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg /{font} {size:.1f} Tf "
            f"{_x(x):.2f} {_y(baseline):.2f} Td ({_esc(s)}) Tj ET"
        )


def build_page() -> Page:
    p = Page()
    left = MIN_PAGE_MARGIN_IN
    right = PAGE_W_IN - MIN_PAGE_MARGIN_IN

    # Wall edge bar and instructions, along the top short edge.
    p.rect(left, 0.4, right - left, 0.42, ORANGE)
    p.text(left + 0.15, 0.71, "WALL EDGE", 18, bold=True, rgb=(1, 1, 1))
    p.text(left + 1.95, 0.69, "this edge of the sheet touches the base of the wall", 11,
           rgb=(1, 1, 1))
    p.text(BOARD_LEFT_IN, 1.1,
           "Lay this sheet flat on the ground with this edge touching the wall.", 10.5)
    p.text(BOARD_LEFT_IN, 1.3, "Keep it flat and uncreased. Weigh the corners down if windy.", 9)

    # Checkerboard: MARKER_COLS along the wall edge, MARKER_ROWS away from it.
    for r in range(MARKER_ROWS):
        for c in range(MARKER_COLS):
            if (r + c) % 2 == 0:
                p.rect(BOARD_LEFT_IN + c * SQUARE_IN, BOARD_TOP_IN + r * SQUARE_IN,
                       SQUARE_IN, SQUARE_IN, (0, 0, 0))
    board_bottom = BOARD_TOP_IN + MARKER_ROWS * SQUARE_IN

    # 4-inch check ruler with quarter-inch ticks.
    ry = board_bottom + 0.4
    x0 = BOARD_LEFT_IN
    p.line(x0, ry, x0 + RULER_IN, ry, 1.2)
    for i in range(int(RULER_IN * 4) + 1):
        x = x0 + i * 0.25
        tick = 0.25 if i % 4 == 0 else (0.16 if i % 2 == 0 else 0.1)
        p.line(x, ry, x, ry + tick, 1.2 if i % 4 == 0 else 0.8)
        if i % 4 == 0:
            p.text(x - 0.03, ry + 0.42, str(i // 4), 9)
    p.text(x0 + RULER_IN + 0.08, ry + 0.42, "in", 9)

    tx = x0 + RULER_IN + 0.35
    p.text(tx, ry + 0.02, "Print at 100% / Actual size", 10.5, bold=True)
    p.text(tx, ry + 0.2, "No fit-to-page scaling. Check:", 9)
    p.text(tx, ry + 0.35, "ruler = exactly 4 in,", 9)
    p.text(tx, ry + 0.5, "each square = exactly 1 in.", 9)
    p.text(BOARD_LEFT_IN, ry + 0.66,
           f"EmberScan scale marker - {MARKER_COLS} x {MARKER_ROWS} squares of "
           f"{SQUARE_IN:g} in", 8, rgb=(0.35, 0.35, 0.35))
    return p


def render_pdf(page: Page) -> bytes:
    """Serialize one page into a minimal PDF 1.4 file (base-14 fonts, no compression)."""
    content = ("\n".join(page.ops) + "\n").encode("latin-1")
    w, h = PAGE_W_IN * PT, PAGE_H_IN * PT
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w:.0f} {h:.0f}] "
            "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
        b"<< /Title (EmberScan scale marker) /Producer (emberscan make_marker_pdf.py) >>",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (
        b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, len(objects), xref)
    )
    return bytes(out)


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else OUT
    page = build_page()
    x0, y0, x1, y1 = page.extent
    m = MIN_PAGE_MARGIN_IN - 1e-9
    if min(x0, y0, PAGE_W_IN - x1, PAGE_H_IN - y1) < m:
        raise SystemExit(f"content extent {page.extent} breaks the {MIN_PAGE_MARGIN_IN} in margin")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(render_pdf(page))
    print(f"wrote {out} ({out.stat().st_size} bytes); content extent (in): "
          f"{x0:.2f}, {y0:.2f} to {x1:.2f}, {y1:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
