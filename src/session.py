import threading
import time
from enum import Enum, auto
from pathlib import Path
from pygame import mixer

INTRO_AUDIO  = Path(__file__).parent.parent / "assets" / "intro_guide.mp3"
EXIT_SIGNAL  = Path(__file__).parent.parent / "assets" / "exit_signal.mp3"


class Phase(Enum):
    IDLE           = auto()
    ENTRY          = auto()   # релаксация 2-3 мин
    ACTIVE_CONCERT = auto()   # активный концерт
    BETWEEN        = auto()   # пауза между концертами 1 мин
    PASSIVE_CONCERT = auto()  # пассивный концерт
    EXIT           = auto()   # плавное завершение
    DONE           = auto()


class SessionPlayer:
    """
    Controls playback of a full two-concert session.
    All callbacks are called from the playback thread — UI must use thread-safe updates.

    Callbacks:
        on_phase_change(phase: Phase)
        on_progress(current: int, total: int)   — word index during concerts
        on_done()
    """

    def __init__(self,
                 active_audio: Path,
                 passive_audio: Path,
                 word_count: int,
                 on_phase_change=None,
                 on_progress=None,
                 on_done=None):

        self.active_audio  = active_audio
        self.passive_audio = passive_audio
        self.word_count    = word_count

        self.on_phase_change = on_phase_change or (lambda p: None)
        self.on_progress     = on_progress     or (lambda c, t: None)
        self.on_done         = on_done         or (lambda: None)

        self._stop_event   = threading.Event()
        self._thread: threading.Thread | None = None
        self.phase         = Phase.IDLE

    # ------------------------------------------------------------------
    def start(self):
        mixer.init(frequency=44100)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Interrupt session (user confirmed)."""
        self._stop_event.set()
        mixer.stop()

    # ------------------------------------------------------------------
    def _set_phase(self, phase: Phase):
        self.phase = phase
        self.on_phase_change(phase)

    def _play_file(self, path: Path, fade_in_ms: int = 0, fade_out_ms: int = 0) -> bool:
        """
        Play an audio file and block until done or stop_event fires.
        Returns True if finished naturally, False if interrupted.
        """
        if not path or not path.exists():
            return True  # skip missing optional files gracefully

        mixer.music.load(str(path))
        mixer.music.play(fade_ms=fade_in_ms)

        while mixer.music.get_busy():
            if self._stop_event.is_set():
                mixer.music.fadeout(1500)
                return False
            time.sleep(0.1)

        return True

    def _silence(self, duration_sec: float) -> bool:
        """Wait for duration or until stop. Returns True if not interrupted."""
        deadline = time.time() + duration_sec
        while time.time() < deadline:
            if self._stop_event.is_set():
                return False
            time.sleep(0.1)
        return True

    # ------------------------------------------------------------------
    def _run(self):
        # --- Phase: ENTRY ---
        self._set_phase(Phase.ENTRY)
        if INTRO_AUDIO.exists():
            if not self._play_file(INTRO_AUDIO, fade_in_ms=2000):
                self._finish()
                return
        else:
            # Fallback: silent relaxation pause of 120 sec
            if not self._silence(120):
                self._finish()
                return

        # --- Phase: ACTIVE CONCERT ---
        self._set_phase(Phase.ACTIVE_CONCERT)
        self.on_progress(0, self.word_count)
        if not self._play_file(self.active_audio, fade_in_ms=1000, fade_out_ms=2000):
            self._finish()
            return
        self.on_progress(self.word_count, self.word_count)

        # --- Phase: BETWEEN ---
        self._set_phase(Phase.BETWEEN)
        if not self._silence(60):
            self._finish()
            return

        # --- Phase: PASSIVE CONCERT ---
        self._set_phase(Phase.PASSIVE_CONCERT)
        self.on_progress(0, self.word_count)
        if not self._play_file(self.passive_audio, fade_in_ms=2000, fade_out_ms=3000):
            self._finish()
            return
        self.on_progress(self.word_count, self.word_count)

        # --- Phase: EXIT ---
        self._set_phase(Phase.EXIT)
        if EXIT_SIGNAL.exists():
            self._play_file(EXIT_SIGNAL)
        else:
            self._silence(5)

        self._finish()

    def _finish(self):
        self._set_phase(Phase.DONE)
        mixer.quit()
        self.on_done()


# ------------------------------------------------------------------
# Convenience: progress tracking for concerts
# Since we play one pre-mixed file per concert (not word-by-word),
# progress is time-based. This helper estimates word index from elapsed time.

class ProgressEstimator:
    """
    Estimates current word index based on elapsed playback time.
    Assumes uniform distribution of words across total duration.
    """

    def __init__(self, word_count: int, total_duration_sec: float):
        self.word_count         = word_count
        self.total_duration_sec = total_duration_sec
        self._start: float | None = None

    def start(self):
        self._start = time.time()

    def current_word(self) -> int:
        if self._start is None:
            return 0
        elapsed = time.time() - self._start
        fraction = min(elapsed / self.total_duration_sec, 1.0)
        return int(fraction * self.word_count)
