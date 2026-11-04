"""Assemble the demo video from captured frames and voiceover blocks.

Each narration block is shown over one or more frames; frame times are
shares of the block's measured audio length. Output is 3840x2160 (4K) H.264
with AAC audio, no music.

Usage: ``uv run python scripts/make_video.py``
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "build" / "video" / "frames4k"
VOICE = ROOT / "build" / "voice"
OUT = ROOT / "build" / "video" / "mamagate-demo.mp4"
GAP = 0.35  # silence between blocks, seconds

# block number -> list of (frame file, share of the block's duration)
TIMELINE = {
    1: [("00_title.png", 0.3), ("00b_problem.png", 0.7)],
    2: [("02_case_loaded.png", 0.25), ("03_gate.png", 0.75)],
    3: [("d1_architecture.png", 0.3), ("04_handoff_running.png", 0.15),
        ("05_handoff_done.png", 0.3), ("07_note.png", 0.25)],
    4: [("06_family_card.png", 0.2), ("06b_card_pidgin.png", 0.2),
        ("06c_card_hausa.png", 0.2), ("06d_card_yoruba.png", 0.2),
        ("06e_card_igbo.png", 0.2)],
    5: [("d2_loop.png", 0.3), ("08_hospital_expected.png", 0.3),
        ("09_hospital_arrived.png", 0.4)],
    6: [("10_dose_refused.png", 0.6), ("d3_safety.png", 0.4)],
    7: [("12_eval.png", 1.0)],
    8: [("13_limits.png", 0.45), ("14_end.png", 0.55)],
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
                 "-vf", ("scale=3840:2160:flags=lanczos:"
                         "force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:"
                         "color=0xF7F8FA,fade=t=in:st=0:d=0.25,"
                         "scale=out_range=tv,format=yuv420p"),
                 "-r", "30", "-c:v", "libx264", "-preset", "slow",
                 "-tune", "stillimage", "-crf", "14", "-pix_fmt", "yuv420p",
                 "-color_range", "tv",
                 str(clip)])
            clips.append(clip)
        padded = work / f"a{n}.wav"
        run(["-i", str(VOICE / f"block_{n}.wav"), "-af",
             f"apad=pad_dur={GAP}", "-ar", "44100", "-ac", "1", str(padded)])
        audio.append(padded)
    (work / "v.txt").write_text("".join(f"file '{c}'\n" for c in clips))
    (work / "a.txt").write_text("".join(f"file '{a}'\n" for a in audio))
    run(["-f", "concat", "-safe", "0", "-i", str(work / "v.txt"),
         "-c:v", "libx264", "-preset", "slow", "-tune", "stillimage",
         "-crf", "14", "-pix_fmt", "yuv420p", "-r", "30",
         str(work / "video.mp4")])
    run(["-f", "concat", "-safe", "0", "-i", str(work / "a.txt"),
         str(work / "voice.wav")])
    run(["-i", str(work / "video.mp4"), "-i", str(work / "voice.wav"),
         "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
         "-shortest",
         "-movflags", "+faststart", str(OUT)])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(OUT)],
        capture_output=True, text=True, check=True)
    print(f"{OUT} {float(probe.stdout):.1f}s")


if __name__ == "__main__":
    main()
