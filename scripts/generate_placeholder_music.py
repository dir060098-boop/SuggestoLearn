from __future__ import annotations
"""
Generates placeholder ambient drone tracks for testing.
Replace output files with real baroque recordings for production use.
See assets/music/README.md for recommendations.
"""
from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

MUSIC_DIR = Path(__file__).parent.parent / "assets" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

TRACKS = [
    # (filename,       bpm,  base_freq, label)
    ("active_vivaldi.mp3",   130, 293.0, "Active — Vivaldi placeholder (D, 130 BPM)"),
    ("active_telemann.mp3",  128, 329.0, "Active — Telemann placeholder (E, 128 BPM)"),
    ("passive_bach.mp3",      60, 220.0, "Passive — Bach placeholder (A, 60 BPM)"),
    ("passive_chopin.mp3",    58, 196.0, "Passive — Chopin placeholder (G, 58 BPM)"),
]


def make_track(bpm: int, duration_sec: int, base_freq: float, output: Path):
    beat_ms   = int(60000 / bpm)
    total_ms  = duration_sec * 1000

    freqs = [base_freq, base_freq * 1.25, base_freq * 1.5, base_freq * 0.5]
    track = AudioSegment.silent(duration=total_ms)

    for freq in freqs:
        tone = Sine(freq).to_audio_segment(duration=total_ms, volume=-22)
        track = track.overlay(tone)

    pulse = Sine(base_freq * 2).to_audio_segment(duration=80, volume=-30).fade_out(80)
    pos = 0
    while pos < total_ms:
        track = track.overlay(pulse, position=pos)
        pos += beat_ms

    track = track.fade_in(3000).fade_out(3000)
    track.export(str(output), format="mp3")


if __name__ == "__main__":
    for filename, bpm, freq, label in TRACKS:
        out = MUSIC_DIR / filename
        if out.exists():
            print(f"  skip (exists): {filename}")
            continue
        print(f"  generating: {label}")
        make_track(bpm, 180, freq, out)
    print("Done.")
