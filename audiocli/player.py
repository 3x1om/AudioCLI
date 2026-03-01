from __future__ import annotations

import shutil
import signal
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field

from .models import Track


@dataclass
class Player:
    queue: deque[Track] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if not shutil.which("mpv"):
            raise RuntimeError("mpv is required. Install it first (e.g., sudo apt install mpv).")
        self._proc: subprocess.Popen[str] | None = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def add(self, track: Track) -> None:
        with self._lock:
            self.queue.append(track)

    def add_front(self, track: Track) -> None:
        with self._lock:
            self.queue.appendleft(track)

    def next(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def stop(self) -> None:
        with self._lock:
            self.queue.clear()
        self.next()

    def pause(self) -> None:
        self._pause.set()
        if self._proc and self._proc.poll() is None:
            self._proc.send_signal(signal.SIGSTOP)

    def resume(self) -> None:
        self._pause.clear()
        if self._proc and self._proc.poll() is None:
            self._proc.send_signal(signal.SIGCONT)

    def shutdown(self) -> None:
        self._stop.set()
        self.next()
        if self._worker.is_alive():
            self._worker.join(timeout=2)

    @property
    def now_playing(self) -> Track | None:
        return getattr(self, "_now", None)

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._pause.is_set():
                self._stop.wait(0.1)
                continue

            track = None
            with self._lock:
                if self.queue:
                    track = self.queue.popleft()
            if not track:
                self._stop.wait(0.1)
                continue

            self._now = track
            self._proc = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--quiet",
                    "--force-window=no",
                    track.stream_url,
                ],
            )
            self._proc.wait()
            self._now = None
