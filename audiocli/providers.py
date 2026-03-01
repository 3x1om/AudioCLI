from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests
from yt_dlp import YoutubeDL

from .models import Track

SPOTIFY_URL_RE = re.compile(r"https?://open\.spotify\.com/(track|album|playlist)/[a-zA-Z0-9]+")


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    source: str
    duration: int | None


class Resolver:
    def __init__(self) -> None:
        self._base_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "discard_in_playlist",
            "skip_download": True,
        }

    def search(self, provider: str, query: str, limit: int = 5) -> list[SearchResult]:
        provider = provider.lower().strip()
        if provider == "youtube":
            term = f"ytsearch{limit}:{query}"
            source = "youtube"
        elif provider == "soundcloud":
            term = f"scsearch{limit}:{query}"
            source = "soundcloud"
        elif provider == "spotify":
            return self._spotify_search(query, limit)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        with YoutubeDL(self._base_opts) as ydl:
            info = ydl.extract_info(term, download=False)
        entries = info.get("entries") or []
        out: list[SearchResult] = []
        for e in entries:
            if not e:
                continue
            out.append(
                SearchResult(
                    title=e.get("title") or "Unknown",
                    url=e.get("webpage_url") or e.get("url") or "",
                    source=source,
                    duration=e.get("duration"),
                )
            )
        return out

    def latest(self, query: str, limit: int = 5) -> list[SearchResult]:
        with YoutubeDL(self._base_opts) as ydl:
            info = ydl.extract_info(f"ytsearchdate{limit}:{query} official music", download=False)
        entries = info.get("entries") or []
        out: list[SearchResult] = []
        for e in entries:
            if not e:
                continue
            out.append(
                SearchResult(
                    title=e.get("title") or "Unknown",
                    url=e.get("webpage_url") or e.get("url") or "",
                    source="youtube-new",
                    duration=e.get("duration"),
                )
            )
        return out

    def download(self, query_or_url: str, output_dir: str = "downloads") -> str:
        target = Path(output_dir).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        source = query_or_url.strip()
        if not self._is_url(source):
            with YoutubeDL(self._base_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{source}", download=False)
            entries = info.get("entries") or []
            if not entries:
                raise RuntimeError("No results found for download.")
            source = entries[0].get("webpage_url") or entries[0].get("url") or source

        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(target / "%(title)s [%(id)s].%(ext)s"),
            "noplaylist": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(source, download=True)
            path = ydl.prepare_filename(info)
        ext = Path(path).suffix
        if ext != ".mp3":
            path = str(Path(path).with_suffix(".mp3"))
        return path

    def resolve(self, query_or_url: str) -> Track:
        q = query_or_url.strip()
        if self._is_url(q):
            if SPOTIFY_URL_RE.search(q):
                return self._resolve_spotify_to_playable(q)
            return self._resolve_direct_url(q)
        return self._resolve_search_query(q)

    def _resolve_direct_url(self, url: str) -> Track:
        opts = dict(self._base_opts)
        opts["format"] = "bestaudio/best"
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if "entries" in info and info["entries"]:
            info = info["entries"][0]
        stream_url = info.get("url")
        if not stream_url:
            raise RuntimeError("Could not extract a playable stream URL.")
        return Track(
            title=info.get("title") or "Unknown",
            webpage_url=info.get("webpage_url") or url,
            stream_url=stream_url,
            source=info.get("extractor_key", "unknown").lower(),
            duration=info.get("duration"),
        )

    def _resolve_search_query(self, query: str) -> Track:
        with YoutubeDL(self._base_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        entries = info.get("entries") or []
        if not entries:
            raise RuntimeError("No search results found.")
        first = entries[0]
        return self._resolve_direct_url(first.get("webpage_url") or first.get("url") or query)

    def _resolve_spotify_to_playable(self, url: str) -> Track:
        title = self._spotify_title_from_url(url)
        if not title:
            raise RuntimeError(
                "Spotify link detected, but metadata lookup failed. "
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET for richer support."
            )
        return self._resolve_search_query(f"{title} official audio")

    def _spotify_title_from_url(self, url: str) -> str | None:
        oembed = f"https://open.spotify.com/oembed?url={quote(url, safe='')}"
        try:
            r = requests.get(oembed, timeout=8)
            r.raise_for_status()
            data = r.json()
            title = data.get("title")
            author = data.get("author_name")
            if title and author and author.lower() not in title.lower():
                return f"{author} - {title}"
            return title
        except Exception:
            pass

        # Optional API fallback for track URLs when credentials are configured.
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not (client_id and client_secret):
            return None
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            creds = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            api = spotipy.Spotify(auth_manager=creds)
            match = re.search(r"/track/([a-zA-Z0-9]+)", url)
            if not match:
                return None
            track = api.track(match.group(1))
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            name = track.get("name")
            if artists and name:
                return f"{artists} - {name}"
            return name
        except Exception:
            return None

    def _spotify_search(self, query: str, limit: int) -> list[SearchResult]:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not (client_id and client_secret):
            # No API keys: return playable fallback results from YouTube.
            fallback = self.search("youtube", f"{query} audio", limit=limit)
            for item in fallback:
                item.source = "spotify-fallback"
            return fallback
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
        except ImportError as e:
            raise RuntimeError("Missing dependency 'spotipy'. Reinstall audiocli to include Spotify search support.") from e

        creds = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        api = spotipy.Spotify(auth_manager=creds)
        data = api.search(q=query, type="track", limit=limit)
        items = data.get("tracks", {}).get("items", [])
        out: list[SearchResult] = []
        for t in items:
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            name = t.get("name", "Unknown")
            title = f"{artists} - {name}" if artists else name
            out.append(
                SearchResult(
                    title=title,
                    url=t.get("external_urls", {}).get("spotify", ""),
                    source="spotify",
                    duration=(t.get("duration_ms") or 0) // 1000,
                )
            )
        return out

    @staticmethod
    def _is_url(text: str) -> bool:
        return text.startswith("http://") or text.startswith("https://")
