from __future__ import annotations
import asyncio
import hashlib
from pathlib import Path
import edge_tts
from pydub import AudioSegment

CACHE_DIR = Path(__file__).parent.parent / "data" / "audio_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Voices
VOICE_MAIN = "en-US-GuyNeural"       # основной голос — мужской, чёткий
VOICE_SUB  = "en-US-AriaNeural"      # субцептивный — женский, мягкий


def _cache_path(text: str, voice: str, rate: str) -> Path:
    key = hashlib.md5(f"{text}|{voice}|{rate}".encode()).hexdigest()
    return CACHE_DIR / f"{key}.mp3"


async def _synthesize(text: str, voice: str, rate: str, output: Path):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output))


def generate_audio(text: str, voice: str = VOICE_MAIN,
                   rate: str = "+0%") -> Path:
    """
    Generate TTS audio with caching. Returns path to .mp3 file.
    rate: edge-tts format, e.g. '-10%' (slower), '+50%' (faster)
    """
    output = _cache_path(text, voice, rate)
    if not output.exists():
        asyncio.run(_synthesize(text, voice, rate, output))
    return output


def build_word_audio(word: str, translation: str, context: str,
                     main_rate: str = "+0%",
                     sub_rate: str = "+50%",
                     sub_volume_db: float = -12.0) -> tuple[Path, Path]:
    """
    Build main and subceptive audio for one vocabulary unit.

    Main track:  word (EN) → translation (RU voice) → context (EN)
    Sub track:   word only, faster, quieter

    Returns (main_path, sub_path) as .mp3 files.
    """
    # --- Main track ---
    word_audio        = AudioSegment.from_mp3(generate_audio(word, VOICE_MAIN, main_rate))
    translation_audio = AudioSegment.from_mp3(generate_audio(translation, "ru-RU-DmitryNeural", main_rate))
    context_audio     = AudioSegment.from_mp3(generate_audio(context, VOICE_MAIN, main_rate))

    pause_short = AudioSegment.silent(duration=400)
    pause_long  = AudioSegment.silent(duration=800)

    main_track = (
        word_audio
        + pause_short
        + translation_audio
        + pause_short
        + context_audio
        + pause_long
    )

    main_key  = hashlib.md5(f"main|{word}|{translation}|{context}|{main_rate}".encode()).hexdigest()
    main_path = CACHE_DIR / f"{main_key}_main.mp3"
    if not main_path.exists():
        main_track.export(main_path, format="mp3")

    # --- Subceptive track ---
    sub_raw   = AudioSegment.from_mp3(generate_audio(word, VOICE_SUB, sub_rate))
    sub_track = sub_raw + sub_volume_db      # lower volume

    sub_key  = hashlib.md5(f"sub|{word}|{sub_rate}|{sub_volume_db}".encode()).hexdigest()
    sub_path = CACHE_DIR / f"{sub_key}_sub.mp3"
    if not sub_path.exists():
        sub_track.export(sub_path, format="mp3")

    return main_path, sub_path


def build_all_audio(words: list[dict],
                    main_rate: str = "+0%",
                    sub_rate: str = "+50%",
                    sub_volume_db: float = -12.0,
                    progress_callback=None) -> list[dict]:
    """
    Generate audio for a list of word dicts.
    Updates each dict with audio_main and audio_sub paths.
    Calls progress_callback(current, total) if provided.
    """
    total = len(words)
    for i, w in enumerate(words):
        main_path, sub_path = build_word_audio(
            w["word"], w["translation"], w["context"],
            main_rate, sub_rate, sub_volume_db
        )
        w["audio_main"] = str(main_path)
        w["audio_sub"]  = str(sub_path)

        if progress_callback:
            progress_callback(i + 1, total)

    return words
