"""Assemble the demo video from captured frames and voiceover blocks.

Each narration block is shown over one or more frames; frame times are
shares of the block's measured audio length. Output is 1920x1080 H.264
with AAC audio, no music.

Usage: ``uv run python scripts/make_video.py``
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "build" / "video" / "frames"
VOICE = ROOT / "build" / "voice"
OUT = ROOT / "build" / "video" / "mamagate-demo.mp4"
GAP = 0.35  # silence between blocks, seconds

# block number -> list of (frame file, share of the block's duration)
TIMELINE = {
    1: [("00_title.jpg", 0.25), ("00b_problem.jpg", 0.75)],
    2: [("02_case_loaded.jpg", 0.22), ("03_gate.jpg", 0.78)],
    3: [("04_handoff_running.jpg", 0.16), ("05_handoff_done.jpg", 0.34),
        ("07_note.jpg", 0.25), ("06_family_card.jpg", 0.25)],
    4: [("08_hospital_expected.jpg", 0.45), ("09_hospital_arrived.jpg", 0.55)],
    5: [("10_dose_refused.jpg", 1.0)],
    6: [("11_how.jpg", 0.4), ("12_eval.jpg", 0.6)],
    7: [("13_limits.jpg", 0.45), ("14_end.jpg", 0.55)],
}


def run(cmd: list[str]) -> None:
    """Run ffmpeg quietly and fail loudly."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cmd], check=True)


def main() -> None:
    """Render clips per frame, join them, and mux the narration."""
    blocks = json.loads((VOICE / "durations.json").read_text())["blocks"]
    work = ROOT / "build" / "video" / "clips"
    work.mkdir(parents=True, exist_ok=True)
    clips, audio = [], []
    for block in blocks:
        n, secs = block["block"], block["seconds"] + GAP
        for i, (frame, share) in enumerate(TIMELINE[n]):
            clip = work / f"b{n}_{i}.mp4"
            dur = round(secs * share, 3)
            run(["-loop", "1", "-t", str(dur), "-i", str(FRAMES / frame),
                 "-vf", ("scale=1920:1080:force_original_aspect_ratio="
                         "decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:"
                         "color=0xF7F8FA,fade=t=in:st=0:d=0.25,format=yuv420p"),
                 "-r", "30", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", str(clip)])
            clips.append(clip)
        padded = work / f"a{n}.wav"
        run(["-i", str(VOICE / f"block_{n}.wav"), "-af",
             f"apad=pad_dur={GAP}", "-ar", "44100", "-ac", "1", str(padded)])
        audio.append(padded)
    (work / "v.txt").write_text("".join(f"file '{c}'\n" for c in clips))
    (work / "a.txt").write_text("".join(f"file '{a}'\n" for a in audio))
    run(["-f", "concat", "-safe", "0", "-i", str(work / "v.txt"),
         "-c", "copy", str(work / "video.mp4")])
    run(["-f", "concat", "-safe", "0", "-i", str(work / "a.txt"),
         str(work / "voice.wav")])
    run(["-i", str(work / "video.mp4"), "-i", str(work / "voice.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(OUT)])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(OUT)],
        capture_output=True, text=True, check=True)
    print(f"{OUT} {float(probe.stdout):.1f}s")


if __name__ == "__main__":
    main()
