"""Draw MamaGate's architecture diagrams in the workshop's visual style.

Rounded boxes (green input, teal agent, amber tool or service, red block),
diamond decisions (blue before-tool, purple after-model) and labelled
arrows (blue proceed, red dashed guide/block), on white. Writes SVG to
``docs/diagrams/``; PNGs are rendered from them with headless Chrome.

Usage: ``uv run python scripts/make_diagrams.py``
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagrams"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

STYLE = {
    "green": ("#E8F5E9", "#2E7D32"),
    "teal": ("#E0F2F1", "#00796B"),
    "amber": ("#FFF3E0", "#EF6C00"),
    "red": ("#FFEBEE", "#C62828"),
    "blue": ("#E3F2FD", "#1565C0"),
    "purple": ("#F3E5F5", "#7B1FA2"),
    "grey": ("#F5F5F5", "#616161"),
}
ARROW = {"blue": "#1E73E8", "red": "#D32F2F", "green": "#2E7D32",
         "purple": "#8E44AD", "grey": "#616161", "teal": "#00796B"}
FONT = "Helvetica, Arial, sans-serif"


class Diagram:
    """A tiny SVG builder for flowcharts."""

    def __init__(self, width: int, height: int, title: str) -> None:
        """Start a diagram with a centred title."""
        self.w, self.h = width, height
        self.parts = [
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
            f'<text x="{width / 2}" y="46" text-anchor="middle" '
            f'font-family="{FONT}" font-size="28" font-weight="700" '
            f'fill="#202124">{title}</text>',
        ]

    def _text(self, x: float, y: float, lines: list[str], size: int = 19,
              color: str = "#202124", weight: str = "400") -> None:
        """Write centred multi-line text around (x, y)."""
        start = y - (len(lines) - 1) * size * 0.62
        for i, line in enumerate(lines):
            self.parts.append(
                f'<text x="{x}" y="{start + i * size * 1.24 + size * 0.35}" '
                f'text-anchor="middle" font-family="{FONT}" '
                f'font-size="{size}" font-weight="{weight}" '
                f'fill="{color}">{line}</text>')

    def box(self, x: float, y: float, w: float, h: float, text: str,
            style: str, size: int = 19, sub: str | None = None) -> None:
        """Draw a rounded box centred at (x, y)."""
        fill, stroke = STYLE[style]
        self.parts.append(
            f'<rect x="{x - w / 2}" y="{y - h / 2}" width="{w}" height="{h}" '
            f'rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        lines = text.split("|")
        if sub:
            self._text(x, y - 9, lines, size)
            self._text(x, y + 9 + (len(lines) - 1) * size * 0.62, [sub],
                       14, "#555555")
        else:
            self._text(x, y, lines, size)

    def diamond(self, x: float, y: float, w: float, h: float, text: str,
                style: str) -> None:
        """Draw a decision diamond centred at (x, y)."""
        fill, stroke = STYLE[style]
        points = (f"{x},{y - h / 2} {x + w / 2},{y} "
                  f"{x},{y + h / 2} {x - w / 2},{y}")
        self.parts.append(f'<polygon points="{points}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="2"/>')
        self._text(x, y, text.split("|"), 17)

    def arrow(self, points: list[tuple[float, float]], color: str,
              label: str | None = None, at: int = 0, dashed: bool = False,
              dx: float = 0, dy: float = -12) -> None:
        """Draw an orthogonal arrow through points, with an optional label."""
        hex_color = ARROW[color]
        path = "M " + " L ".join(f"{px},{py}" for px, py in points)
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        self.parts.append(
            f'<path d="{path}" fill="none" stroke="{hex_color}" '
            f'stroke-width="2.4"{dash} marker-end="url(#a-{color})"/>')
        if label:
            (x1, y1), (x2, y2) = points[at], points[at + 1]
            self.parts.append(
                f'<text x="{(x1 + x2) / 2 + dx}" y="{(y1 + y2) / 2 + dy}" '
                f'text-anchor="middle" font-family="{FONT}" font-size="19" '
                f'fill="{hex_color}">{label}</text>')

    def note(self, x: float, y: float, text: str) -> None:
        """Write a small grey caption line."""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="16" '
            f'fill="#5F6368">{text}</text>')

    def svg(self) -> str:
        """Return the finished SVG document."""
        markers = "".join(
            f'<marker id="a-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>'
            for name, col in ARROW.items())
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}"><defs>{markers}</defs>'
                + "".join(self.parts) + "</svg>")


def architecture() -> Diagram:
    """End-to-end architecture: worker, gate, agent, AWS, hospital."""
    d = Diagram(1700, 940, "MamaGate architecture")
    d.box(130, 300, 200, 80, "CHEW enters|findings", "green")
    d.arrow([(230, 300), (290, 300)], "grey")
    d.diamond(400, 300, 220, 160, "Rules gate|35 rules · code", "blue")
    d.arrow([(510, 300), (700, 300)], "blue", "REFER NOW / 24H")
    d.arrow([(400, 380), (400, 470)], "grey", "ROUTINE", dx=48, dy=4)
    d.box(400, 520, 260, 80, "Follow-up actions +|birth preparedness",
          "amber")
    d.arrow([(400, 220), (400, 150), (700, 150)], "red", "dose request",
            at=1, dashed=True)
    d.box(800, 150, 200, 70, "Refused in code", "red")
    # Agent runtime container
    d.parts.append('<rect x="700" y="220" width="560" height="380" rx="14" '
                   'fill="#E0F2F1" stroke="#00796B" stroke-width="2.4"/>')
    d._text(980, 250, ["Strands agent on Amazon Bedrock AgentCore Runtime"],
            20, "#00695C", "700")
    d.box(830, 320, 220, 64, "Skills|referral-handoff", "teal", 16)
    d.box(1130, 320, 220, 64, "Steering|workflow + language", "teal", 16)
    d.box(830, 410, 220, 64, "Hooks|gate+dose lock, rate limit", "teal", 16)
    d.box(1130, 410, 220, 64, "Writer specialist|agents as tools", "teal",
          16)
    d.box(830, 500, 220, 64, "Tools|9 @tool functions", "teal", 16)
    d.box(1130, 500, 220, 64, "Session|S3SessionManager", "teal", 16)
    d.note(720, 585, "Bedrock model: Claude Sonnet · traces to CloudWatch")
    # AWS services
    services = [("Amazon Location|road time", 1440, 260),
                ("Amazon SNS|pre-alert", 1440, 370),
                ("EventBridge|Scheduler", 1440, 480),
                ("Amazon S3|sessions", 1440, 590)]
    for text, x, y in services:
        d.box(x, y, 220, 76, text, "amber", 17)
        d.arrow([(1260, y), (1330, y)], "teal")
    # Hospital loop
    d.box(980, 730, 300, 80, "Hospital view|incoming referral", "green")
    d.arrow([(1550, 370), (1615, 370), (1615, 730), (1130, 730)], "blue",
            "pre-alert", at=2, dy=-12)
    d.diamond(620, 730, 220, 140, "Arrived?", "purple")
    d.arrow([(830, 730), (730, 730)], "grey")
    d.arrow([(620, 660), (620, 640), (370, 640), (370, 690)], "green",
            "yes: cancel alert", at=1)
    d.box(370, 730, 240, 70, "Loop closed|clinic notified", "green", 17)
    d.arrow([(620, 800), (620, 856), (500, 856)], "red", "no", at=1,
            dashed=True, dy=-10)
    d.box(370, 856, 260, 56, "Supervisor alerted", "red", 17)
    d.note(60, 912, "Why: urgency is decided by code before any model runs; "
           "the agent only coordinates the handoff, and the loop ends at a "
           "confirmed arrival.")
    return d


def safety() -> Diagram:
    """Steering and hooks, laid out like the workshop's steering figure."""
    d = Diagram(1700, 860, "MamaGate safety layers")
    d.box(150, 430, 220, 80, "CHEW request", "green")
    d.arrow([(260, 430), (330, 430)], "green")
    d.diamond(440, 430, 220, 150, "Dose|request?", "red")
    d.arrow([(440, 355), (440, 160), (640, 160)], "red", "yes", at=1,
            dashed=True)
    d.box(790, 160, 290, 76, "Refused in code|no model called", "red", 18)
    d.arrow([(550, 430), (640, 430)], "grey", "no", dy=-12)
    d.box(740, 430, 200, 80, "Agent Loop", "teal")
    d.arrow([(840, 430), (900, 430), (900, 330), (1000, 330)], "blue",
            "before tool call", at=1, dx=-80, dy=0)
    d.diamond(1120, 330, 240, 150, "Workflow +|gate/dose lock", "blue")
    d.arrow([(1120, 255), (1120, 210), (1300, 210)], "blue", "Proceed",
            at=1)
    d.box(1440, 210, 260, 70, "Tool runs|(pre-alert, schedule)", "amber",
          17)
    d.arrow([(1120, 405), (1120, 440), (1300, 440)], "red",
            "Guide / cancel", at=1, dashed=True)
    d.box(1440, 440, 260, 70, "Verify the note first|or remove the dose",
          "red", 17)
    d.arrow([(840, 450), (900, 450), (900, 640), (1000, 640)], "purple",
            "after model turn", at=1, dx=-82, dy=0)
    d.diamond(1120, 640, 240, 150, "Language|review (LLM)", "purple")
    d.arrow([(1120, 565), (1120, 560), (1300, 560)], "green", "Approved",
            at=1)
    d.box(1440, 560, 260, 64, "Reply sent|(doses redacted)", "green", 17)
    d.arrow([(1120, 715), (1120, 740), (1300, 740)], "red", "Needs fix",
            at=1, dashed=True)
    d.box(1440, 740, 260, 64, "Revise: no diagnosis,|no reassurance",
          "red", 17)
    d.note(60, 832, "Why: rules that must never fail are code (dose refusal, "
           "tool order, urgency floor); judgement calls go to an LLM "
           "reviewer.")
    return d


def referral_loop() -> Diagram:
    """Draw the closed referral loop between two facilities."""
    d = Diagram(1700, 700, "MamaGate referral loop")
    steps = [("Danger sign|found", "green", 130),
             ("Hospital|chosen", "amber", 370),
             ("Note written|+ checked", "teal", 610),
             ("Pre-alert|Amazon SNS", "amber", 850),
             ("Arrival check|EventBridge", "amber", 1090)]
    for i, (text, style, x) in enumerate(steps):
        d.box(x, 220, 200, 90, text, style, 18)
        if i:
            d.arrow([(x - 140, 220), (x - 100, 220)], "blue")
    d.arrow([(1190, 220), (1300, 220)], "blue")
    d.diamond(1420, 220, 220, 150, "Arrived in|time?", "purple")
    d.arrow([(1420, 295), (1420, 400)], "green", "yes", dx=26, dy=4)
    d.box(1420, 450, 300, 90, "Hospital marks arrived:|schedule deleted",
          "green", 18)
    d.arrow([(1530, 220), (1600, 220), (1600, 600), (1300, 600)], "red",
            "no", at=1, dashed=True, dx=20, dy=0)
    d.box(1120, 600, 320, 80, "Supervisor alerted:|contact the family",
          "red", 18)
    d.arrow([(1270, 450), (900, 450)], "green", "clinic notified")
    d.box(780, 450, 220, 80, "Clinic closes|the case", "green", 18)
    d.note(60, 672, "Why: in Kano only 1 in 10 referred women completed the "
           "referral; a missed referral must be noticed, not lost.")
    return d


def main() -> None:
    """Write SVG and PNG versions of every diagram."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in (("architecture", architecture),
                        ("safety-layers", safety),
                        ("referral-loop", referral_loop)):
        diagram = build()
        svg = OUT / f"{name}.svg"
        svg.write_text(diagram.svg(), encoding="utf-8")
        png = OUT / f"{name}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={diagram.w},{diagram.h}",
             f"--screenshot={png}", f"file://{svg}"],
            check=True, capture_output=True)
        print(png)


if __name__ == "__main__":
    main()
