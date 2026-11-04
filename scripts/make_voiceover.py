"""Generate the demo voiceover, one audio file per narration block.

Reads the narration from ``docs/video/script.md``. Uses Aethex
(Nigerian English voice) when ``AETHEX_API_KEY`` works, otherwise
Amazon Polly's Ayanda generative voice (South African English).

Usage: ``uv run python scripts/make_voiceover.py [--engine polly|aethex]``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs" / "video" / "script.md"
OUT = ROOT / "build" / "voice"
AETHEX_URL = "https://api.aethexai.com/api/v1/tts"
AETHEX_VOICE = os.environ.get(
    "AETHEX_VOICE_ID", "8466fb57-9f6b-53ad-ba5a-9729617f761c")  # Kemi, NG


def narration_blocks() -> list[str]:
    """Return the narration paragraphs in order."""
    text = SCRIPT.read_text(encoding="utf-8")
    body = text.split("## Narration")[1]
    body = re.split(r"## (?:Language clips|On-screen)", body)[0]
    parts = re.split(r"\*\*\d\..*?\*\*", body)
    return [" ".join(p.split()) for p in parts if p.strip()]


def aethex(text: str, path: Path) -> None:
    """Synthesise one block with Aethex (WAV, 24 kHz mono)."""
    request = urllib.request.Request(
        AETHEX_URL,
        data=json.dumps({"text": text, "language": "english",
                         "voice_id": AETHEX_VOICE}).encode(),
        headers={"X-API-Key": os.environ["AETHEX_API_KEY"],
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        path.write_bytes(response.read())


def polly(text: str, path: Path) -> None:
    """Synthesise one block with Amazon Polly (Ayanda, generative)."""
    import boto3

    client = boto3.client("polly", region_name="us-east-1")
    audio = client.synthesize_speech(
        Text=text, VoiceId="Ayanda", Engine="generative", OutputFormat="mp3",
        SampleRate="24000")
    mp3 = path.with_suffix(".mp3")
    mp3.write_bytes(audio["AudioStream"].read())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
                    str(path)], check=True)
    mp3.unlink()


def duration(path: Path) -> float:
    """Return an audio file's duration in seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout)


def language_clips() -> list[tuple[str, str, str, str | None]]:
    """Return (code, text, aethex language, voice) for the video clips."""
    import sys

    sys.path.insert(0, str(ROOT))
    from mamagate.languages import VOICES, card_in

    clips = []
    for code in ("pcm", "ha", "yo"):
        card = card_in(code, urgent=True)
        text = (f"{card['headline']} {card['signs_title']}: "
                + ", ".join(card["signs"][:3]) + ".")
        clips.append((code, text, *VOICES[code]))
    return clips


def aethex_clip(text: str, language: str, voice: str | None,
                path: Path) -> None:
    """Synthesise one language clip with Aethex."""
    body = {"text": text, "language": language}
    if voice:
        body["voice_id"] = voice
    request = urllib.request.Request(
        AETHEX_URL, data=json.dumps(body).encode(),
        headers={"X-API-Key": os.environ["AETHEX_API_KEY"],
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
        path.write_bytes(response.read())


def main() -> None:
    """Write block_N.wav files and a durations.json manifest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["aethex", "polly"],
                        default="aethex")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, text in enumerate(narration_blocks(), start=1):
        path = OUT / f"block_{i}.wav"
        (aethex if args.engine == "aethex" else polly)(text, path)
        manifest.append({"block": i, "seconds": round(duration(path), 2),
                         "chars": len(text)})
        print(manifest[-1])
    clips = []
    if args.engine == "aethex":
        for code, text, language, voice in language_clips():
            path = OUT / f"lang_{code}.wav"
            aethex_clip(text, language, voice, path)
            clips.append({"language": code,
                          "seconds": round(duration(path), 2)})
            print(clips[-1])
    (OUT / "durations.json").write_text(json.dumps(
        {"engine": args.engine, "blocks": manifest, "clips": clips},
        indent=2))
    print("total", round(sum(m["seconds"] for m in manifest), 1), "s")


if __name__ == "__main__":
    main()
