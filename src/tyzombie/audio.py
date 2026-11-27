"""Zero-dependency cross-platform synthesized audio engine."""

from __future__ import annotations

import math
import os
import queue
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave

# Event -> list of (frequency_hz, duration_ms)
SOUND_CUES = {
    "hit": [(880, 18)],
    "kill": [(520, 40), (780, 55)],
    "power": [(440, 45), (660, 45), (880, 70)],
    "bomb": [(180, 90), (120, 110)],
    "damage": [(160, 130)],
    "boss": [(220, 100), (196, 120), (175, 160)],
    "clear": [(523, 70), (659, 70), (784, 70), (1046, 140)],
    "gameover": [(330, 120), (262, 140), (196, 220)],
    "typo": [(210, 40)],
}


def _synthesize_wav(path, tones, sample_rate=22050, volume=0.25):
    """Write a sequence of (freq, duration_ms) sine tones to a mono 16-bit WAV."""
    frames = bytearray()
    for freq, dur_ms in tones:
        count = max(1, int(sample_rate * dur_ms / 1000.0))
        fade = min(count // 4, int(sample_rate * 0.008))
        for i in range(count):
            env = 1.0
            if fade > 0:
                if i < fade:
                    env = i / fade
                elif i > count - fade:
                    env = (count - i) / fade
            sample = math.sin(2.0 * math.pi * freq * i / sample_rate) * volume * env
            frames.extend(struct.pack("<h", max(-32767, min(32767, int(sample * 32767)))))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


class AudioEngine:
    """Non-blocking sound effect player using stdlib only."""

    def __init__(self, enabled=True):
        self.enabled = bool(enabled)
        self._queue: queue.Queue[str | None] = queue.Queue(maxsize=16)
        self._stop = threading.Event()
        self._cache: dict[str, str] = {}
        self._tmpdir: str | None = None
        self._unix_player: str | None = self._detect_unix_player()
        self._worker = threading.Thread(target=self._run, name="tyzombie-audio", daemon=True)
        self._worker.start()

    @staticmethod
    def _detect_unix_player() -> str | None:
        if sys.platform == "darwin":
            return shutil.which("afplay")
        if sys.platform.startswith("linux"):
            return shutil.which("paplay") or shutil.which("aplay")
        return None

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def play(self, cue):
        """Queue a named sound cue without blocking the game loop."""
        if not self.enabled or cue not in SOUND_CUES:
            return
        try:
            self._queue.put_nowait(cue)
        except queue.Full:
            pass

    def close(self):
        """Stop the background worker and clean up temporary WAV files."""
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._tmpdir and os.path.isdir(self._tmpdir):
            for fname in list(self._cache.values()):
                try:
                    os.remove(fname)
                except OSError:
                    pass
            try:
                os.rmdir(self._tmpdir)
            except OSError:
                pass

    def _run(self):
        while not self._stop.is_set():
            try:
                cue = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if cue is None:
                break
            if not self.enabled:
                continue
            self._play_sync(cue)

    def _play_sync(self, cue):
        tones = SOUND_CUES.get(cue, [])
        if not tones:
            return
        if sys.platform == "win32":
            try:
                import winsound
                for freq, dur in tones:
                    if not self.enabled or self._stop.is_set():
                        break
                    winsound.Beep(max(37, min(32767, freq)), max(10, dur))
            except Exception:
                pass
            return

        player = self._unix_player
        if not isinstance(player, str):
            return
        if not player:
            return
        try:
            if cue not in self._cache:
                if self._tmpdir is None:
                    self._tmpdir = tempfile.mkdtemp(prefix="tyzombie_audio_")
                wav_path = os.path.join(self._tmpdir, f"{cue}.wav")
                _synthesize_wav(wav_path, tones)
                self._cache[cue] = wav_path
            # pyrefly: ignore[bad-assignment]
            cmd: list[str] = [player, self._cache[cue]]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        except Exception:
            pass
