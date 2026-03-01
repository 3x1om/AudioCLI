from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Callable

from .player import Player
from .providers import Resolver


class App:
    def __init__(self) -> None:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("This app is Linux-only.")
        self.resolver = Resolver()
        self.player = Player()
        self._commands: dict[str, Callable[[str], None]] = {
            "help": self.cmd_help,
            "play": self.cmd_play,
            "add": self.cmd_add,
            "download": self.cmd_download,
            "updates": self.cmd_updates,
            "search": self.cmd_search,
            "queue": self.cmd_queue,
            "np": self.cmd_now_playing,
            "next": self.cmd_next,
            "pause": self.cmd_pause,
            "resume": self.cmd_resume,
            "stop": self.cmd_stop,
            "clear": self.cmd_clear,
            "quit": self.cmd_quit,
            "exit": self.cmd_quit,
        }
        self._running = True

    def run(self) -> None:
        self._repair_terminal()
        print("audiocli (linux) - type 'help' for commands")
        while self._running:
            try:
                raw = input("audiocli> ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not raw:
                continue
            parts = shlex.split(raw)
            cmd = parts[0].lower()
            arg = raw[len(parts[0]) :].strip()
            handler = self._commands.get(cmd)
            if not handler:
                # Treat free text as an implicit "play" query for faster UX.
                try:
                    self.cmd_play(raw)
                except Exception as e:
                    print(f"Unknown command: {cmd} ({e})")
                continue
            try:
                handler(arg)
            except Exception as e:
                print(f"Error: {e}")
        try:
            self.player.shutdown()
        except KeyboardInterrupt:
            pass
        self._repair_terminal()

    def cmd_help(self, _: str) -> None:
        print(
            "\n".join(
                [
                    "play <query_or_url> [--repeat N|--repeated]  resolve and play immediately",
                    "add <query_or_url> [--repeat N|--repeated]   resolve and add to queue",
                    "download <query_or_url> [--path DIR]  download local audio copy",
                    "updates <query>          latest music uploads for query",
                    "search <provider> <q>    provider = youtube|soundcloud|spotify",
                    "queue                    show pending queue",
                    "np                       show now playing",
                    "next                     skip current track",
                    "pause                    pause playback",
                    "resume                   resume playback",
                    "stop                     stop and clear queue",
                    "clear                    clear queued tracks",
                    "quit                     exit app",
                ]
            )
        )

    def cmd_play(self, arg: str) -> None:
        if not arg:
            raise ValueError("Usage: play <query_or_url>")
        query, repeat_count = self._parse_repeat_arg(arg)
        track = self.resolver.resolve(query)
        track.repeat_count = repeat_count
        self.player.add_front(track)
        self.player.next()
        suffix = f" ({repeat_count}x)" if repeat_count > 1 else ""
        print(f"Queued (front): {track.title}{suffix}")

    def cmd_add(self, arg: str) -> None:
        if not arg:
            raise ValueError("Usage: add <query_or_url>")
        query, repeat_count = self._parse_repeat_arg(arg)
        track = self.resolver.resolve(query)
        track.repeat_count = repeat_count
        self.player.add(track)
        suffix = f" ({repeat_count}x)" if repeat_count > 1 else ""
        print(f"Queued: {track.title}{suffix}")

    def cmd_download(self, arg: str) -> None:
        if not arg:
            raise ValueError("Usage: download <query_or_url> [--path DIR]")
        query, out_dir = self._parse_download_args(arg)
        out = self.resolver.download(query, output_dir=out_dir)
        print(f"Downloaded: {out}")

    def cmd_updates(self, arg: str) -> None:
        query = arg.strip()
        if not query:
            raise ValueError("Usage: updates <query>")
        results = self.resolver.latest(query, limit=5)
        if not results:
            print("No recent tracks found.")
            return
        for i, r in enumerate(results, start=1):
            dur = "--:--"
            if r.duration:
                m, s = divmod(r.duration, 60)
                dur = f"{m}:{s:02d}"
            print(f"{i}. [{r.source}] {r.title} ({dur})")
            print(f"   {r.url}")

    def cmd_search(self, arg: str) -> None:
        parts = shlex.split(arg)
        if len(parts) < 2:
            raise ValueError("Usage: search <provider> <query>")
        provider = parts[0]
        query = " ".join(parts[1:])
        results = self.resolver.search(provider, query, limit=5)
        if not results:
            print("No results.")
            return
        for i, r in enumerate(results, start=1):
            dur = "--:--"
            if r.duration:
                m, s = divmod(r.duration, 60)
                dur = f"{m}:{s:02d}"
            print(f"{i}. [{r.source}] {r.title} ({dur})")
            print(f"   {r.url}")

    def cmd_queue(self, _: str) -> None:
        if not self.player.queue:
            print("Queue is empty.")
            return
        for i, t in enumerate(self.player.queue, start=1):
            suffix = f" [{t.repeat_count}x]" if t.repeat_count > 1 else ""
            print(f"{i}. {t.title} [{t.pretty_duration}]{suffix} - {t.webpage_url}")

    def cmd_now_playing(self, _: str) -> None:
        track = self.player.now_playing
        if not track:
            print("Nothing playing.")
            return
        suffix = f" [{track.repeat_count}x left]" if track.repeat_count > 1 else ""
        print(f"Now playing: {track.title} [{track.pretty_duration}]{suffix}")
        print(track.webpage_url)

    def cmd_next(self, _: str) -> None:
        self.player.next()
        print("Skipped.")

    def cmd_pause(self, _: str) -> None:
        self.player.pause()
        print("Paused.")

    def cmd_resume(self, _: str) -> None:
        self.player.resume()
        print("Resumed.")

    def cmd_stop(self, _: str) -> None:
        self.player.stop()
        print("Stopped and cleared queue.")

    def cmd_clear(self, _: str) -> None:
        self.player.queue.clear()
        print("Queue cleared.")

    def cmd_quit(self, _: str) -> None:
        self._running = False

    @staticmethod
    def _parse_repeat_arg(arg: str) -> tuple[str, int]:
        parts = shlex.split(arg)
        repeat_count = 1
        cleaned: list[str] = []
        i = 0
        while i < len(parts):
            part = parts[i]
            if part in ("--repeat", "--repeated"):
                repeat_count = 2
                if i + 1 < len(parts):
                    nxt = parts[i + 1]
                    if nxt.isdigit():
                        repeat_count = int(nxt)
                        i += 1
                    elif nxt.startswith("--repeat="):
                        value = nxt.split("=", 1)[1]
                        if not value.isdigit():
                            raise ValueError("--repeat must be a positive integer.")
                        repeat_count = int(value)
                        i += 1
            elif part.startswith("--repeat="):
                value = part.split("=", 1)[1]
                if not value.isdigit():
                    raise ValueError("--repeat must be a positive integer.")
                repeat_count = int(value)
            if repeat_count < 1:
                raise ValueError("--repeat must be a positive integer.")
            elif not part.startswith("--repeat"):
                cleaned.append(part)
            i += 1
        query = " ".join(cleaned).strip()
        if not query:
            raise ValueError("Missing query_or_url.")
        return query, repeat_count

    @staticmethod
    def _parse_download_args(arg: str) -> tuple[str, str]:
        parts = shlex.split(arg)
        out_dir = "downloads"
        cleaned: list[str] = []
        i = 0
        while i < len(parts):
            if parts[i] == "--path":
                i += 1
                if i >= len(parts):
                    raise ValueError("Usage: download <query_or_url> [--path DIR]")
                out_dir = parts[i]
            else:
                cleaned.append(parts[i])
            i += 1
        query = " ".join(cleaned).strip()
        if not query:
            raise ValueError("Usage: download <query_or_url> [--path DIR]")
        return query, out_dir

    @staticmethod
    def _repair_terminal() -> None:
        # Restore a sane TTY state after interrupted playback sessions.
        subprocess.run(["stty", "sane"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
