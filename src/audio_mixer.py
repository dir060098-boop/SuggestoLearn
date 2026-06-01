import hashlib
from pathlib import Path
from pydub import AudioSegment

CACHE_DIR  = Path(__file__).parent.parent / "data" / "audio_cache"
ASSETS_DIR = Path(__file__).parent.parent / "assets" / "music"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Built-in music tracks
MUSIC_TRACKS = {
    "active_vivaldi":  ASSETS_DIR / "active_vivaldi.mp3",
    "active_telemann": ASSETS_DIR / "active_telemann.mp3",
    "passive_bach":    ASSETS_DIR / "passive_bach.mp3",
    "passive_chopin":  ASSETS_DIR / "passive_chopin.mp3",
}

DEFAULT_ACTIVE_MUSIC  = "active_vivaldi"
DEFAULT_PASSIVE_MUSIC = "passive_bach"


def _loop_music(music: AudioSegment, target_ms: int) -> AudioSegment:
    """Loop or trim music to match target duration."""
    if len(music) >= target_ms:
        return music[:target_ms]
    loops = (target_ms // len(music)) + 1
    return (music * loops)[:target_ms]


def _mix_sub_into_main(main: AudioSegment, sub: AudioSegment,
                       offset_ms: int) -> AudioSegment:
    """Overlay subceptive audio into main track at pause position."""
    if offset_ms + len(sub) > len(main):
        return main
    return main.overlay(sub, position=offset_ms)


def build_concert_audio(words: list[dict],
                        concert_type: str = "active",
                        music_key: str | None = None,
                        music_volume_db: float = -14.0,
                        custom_music_path: str | None = None) -> Path:
    """
    Build final mixed .mp3 for one concert phase.

    concert_type: 'active' or 'passive'
    Returns path to mixed .mp3 file.
    """
    # Choose music
    if custom_music_path:
        music_path = Path(custom_music_path)
    else:
        key = music_key or (DEFAULT_ACTIVE_MUSIC if concert_type == "active"
                            else DEFAULT_PASSIVE_MUSIC)
        music_path = MUSIC_TRACKS.get(key)

    # Assemble speech track
    speech = AudioSegment.empty()
    sub_positions: list[tuple[int, AudioSegment]] = []

    for w in words:
        main_audio = AudioSegment.from_mp3(w["audio_main"])
        sub_audio  = AudioSegment.from_mp3(w["audio_sub"])

        # Subceptive voice goes into the trailing pause of main audio
        # (last 1000ms of each word segment)
        sub_offset = len(speech) + max(0, len(main_audio) - 1000)
        sub_positions.append((sub_offset, sub_audio))

        speech += main_audio

    # Overlay subceptive voices (active concert only)
    if concert_type == "active":
        for offset, sub in sub_positions:
            speech = _mix_sub_into_main(speech, sub, offset)

    # Fade-in / fade-out on speech
    speech = speech.fade_in(2000).fade_out(2000)

    # Mix music under speech
    if music_path and music_path.exists():
        music = AudioSegment.from_mp3(str(music_path)) + music_volume_db
        music = _loop_music(music, len(speech))
        mixed = music.overlay(speech)
    else:
        mixed = speech

    # Cache by content hash
    word_ids = "|".join(str(w.get("id", w["word"])) for w in words)
    cache_key = hashlib.md5(
        f"{concert_type}|{music_path}|{word_ids}".encode()
    ).hexdigest()
    output_path = CACHE_DIR / f"concert_{concert_type}_{cache_key}.mp3"

    if not output_path.exists():
        mixed.export(output_path, format="mp3")

    return output_path


def build_session_audio(words: list[dict],
                        active_music: str | None = None,
                        passive_music: str | None = None,
                        active_music_volume: float = -14.0,
                        passive_music_volume: float = -10.0,
                        custom_active_path: str | None = None,
                        custom_passive_path: str | None = None) -> dict:
    """
    Build both concert files for a full session.
    Returns {active: Path, passive: Path}
    """
    active_path = build_concert_audio(
        words,
        concert_type="active",
        music_key=active_music,
        music_volume_db=active_music_volume,
        custom_music_path=custom_active_path,
    )

    passive_path = build_concert_audio(
        words,
        concert_type="passive",
        music_key=passive_music,
        music_volume_db=passive_music_volume,
        custom_music_path=custom_passive_path,
    )

    return {"active": active_path, "passive": passive_path}
