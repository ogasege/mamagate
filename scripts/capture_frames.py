"""Capture crisp 4K video frames of the live MamaGate app.

Drives the web UI with Playwright and the locally installed Google
Chrome at a 1920x1080 viewport and device scale factor 2, so every frame
is 3840x2160. Needs ``server.py`` running on port 8899 (against the
AgentCore runtime) and the slide server on port 8901.

Usage: ``uv run python scripts/capture_frames.py``
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "build" / "video" / "frames4k"
APP = "http://localhost:8899/"
SLIDES = "http://localhost:8901/docs/video/slides/"


def shot(page: Page, name: str) -> None:
    """Save a full-viewport screenshot."""
    page.mouse.move(1915, 1075)
    page.screenshot(path=str(FRAMES / name), type="png")
    print("saved", name)


def wait_done(page: Page, timeout: float = 240_000) -> None:
    """Wait until the run button is enabled again (agent finished)."""
    page.wait_for_function(
        "() => !document.querySelector('#run').disabled", timeout=timeout)
    page.wait_for_timeout(4500)  # let the flowing timeline finish


def main() -> None:
    """Capture every frame used by scripts/make_video.py."""
    FRAMES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
                                  device_scale_factor=2,
                                  color_scheme="light")
        page = ctx.new_page()
        for slide, name in (("title.html", "00_title.png"),
                            ("problem.html", "00b_problem.png"),
                            ("end.html", "14_end.png")):
            page.goto(SLIDES + slide)
            page.wait_for_timeout(600)
            shot(page, name)
        for svg, name in (("architecture", "d1_architecture.png"),
                          ("referral-loop", "d2_loop.png"),
                          ("safety-layers", "d3_safety.png")):
            page.goto("about:blank")
            page.set_content(
                "<html><body style='margin:0;background:#fff;display:flex;"
                "align-items:center;justify-content:center;height:100vh'>"
                f"<img src='http://localhost:8901/docs/diagrams/{svg}.svg' "
                "style='width:94vw;max-height:94vh;object-fit:contain'>"
                "</body></html>")
            page.wait_for_timeout(400)
            shot(page, name)

        page.goto(APP)
        page.wait_for_timeout(800)
        page.select_option("#preset", "pe")
        page.wait_for_timeout(300)
        shot(page, "02_case_loaded.png")
        page.click("#run")
        page.wait_for_selector(".badge")
        page.wait_for_timeout(1200)
        shot(page, "03_gate.png")
        page.wait_for_timeout(5000)
        shot(page, "04_handoff_running.png")
        wait_done(page)
        shot(page, "05_handoff_done.png")
        page.click("#view-note")
        page.wait_for_timeout(500)
        shot(page, "07_note.png")
        page.click("#close")
        col = "document.querySelectorAll('.col')[2]"
        page.evaluate(f"{col}.scrollTop = {col}.scrollHeight")
        page.wait_for_timeout(300)
        for lang, name in (("en", "06_family_card.png"),
                           ("pcm", "06b_card_pidgin.png"),
                           ("ha", "06c_card_hausa.png"),
                           ("yo", "06d_card_yoruba.png"),
                           ("ig", "06e_card_igbo.png")):
            page.click(f"[data-lang={lang}]")
            page.wait_for_timeout(300)
            page.evaluate(f"{col}.scrollTop = {col}.scrollHeight")
            shot(page, name)

        page.click("[data-view=hospital]")
        page.wait_for_timeout(1200)
        shot(page, "08_hospital_expected.png")
        page.click("[data-arr][data-v='1']")
        page.wait_for_timeout(4000)
        shot(page, "09_hospital_arrived.png")

        page.click("[data-view=consult]")
        page.select_option("#preset", "dose")
        page.click("#run")
        wait_done(page, 120_000)
        shot(page, "10_dose_refused.png")

        for view, name in (("how", "11_how.png"), ("eval", "12_eval.png"),
                           ("limits", "13_limits.png")):
            page.click(f"[data-view={view}]")
            page.wait_for_timeout(1500)
            shot(page, name)
        browser.close()


if __name__ == "__main__":
    main()
