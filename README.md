# audiocli

Linux-only terminal music player that resolves user queries/links and plays audio with `mpv`.

Supported flow:
- YouTube links + search
- SoundCloud links + search
- Spotify links (resolved to playable audio by searching for the same track)
- Spotify search (works without API keys via fallback)
- Many other sites supported by `yt-dlp` links

## Important notes
- Spotify streams are DRM-protected; this app does **not** play Spotify streams directly.
- For Spotify links, the app fetches track metadata and resolves to a playable source.
- The app itself does not inject ads.

## Requirements (Linux)
- `python >= 3.11`
- `mpv`
- internet connection

## One command install + run (all major Linux distros)

```bash
bash -lc 'set -e; if [ -d .git ] && git config --get remote.origin.url | grep -q "3x1om/audiocli"; then REPO_DIR="."; elif [ -d audiocli/.git ]; then REPO_DIR="audiocli"; git -C "$REPO_DIR" pull --ff-only; else git clone https://github.com/3x1om/audiocli.git audiocli; REPO_DIR="audiocli"; fi; cd "$REPO_DIR"; if command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y mpv ffmpeg python3 python3-pip; elif command -v dnf >/dev/null; then sudo dnf install -y mpv ffmpeg python3 python3-pip; elif command -v pacman >/dev/null; then sudo pacman -Sy --noconfirm mpv ffmpeg python python-pip; elif command -v zypper >/dev/null; then sudo zypper --non-interactive install mpv ffmpeg python3 python3-pip; elif command -v apk >/dev/null; then sudo apk add mpv ffmpeg python3 py3-pip; else echo "Unsupported distro: install mpv ffmpeg python3 python3-pip manually."; exit 1; fi; python3 -m ensurepip --upgrade || true; python3 -m pip install --user --no-build-isolation -e .; hash -r; audiocli'
```

## One command uninstall

```bash
python3 -m pip uninstall -y audiocli
```

## Commands

```text
play <query_or_url> [--repeat N|--repeated]  resolve and play immediately
add <query_or_url> [--repeat N|--repeated]   resolve and add to queue
download <query_or_url> [--path DIR]  download local audio copy
updates <query>          latest music uploads for query
search <provider> <q>    provider = youtube|soundcloud|spotify
queue                    show pending queue
np                       show now playing
next                     skip current track
pause                    pause playback
resume                   resume playback
stop                     stop and clear queue
clear                    clear queued tracks
quit                     exit app
```

## Examples

```text
play daft punk harder better faster stronger
play montagem rugada --repeated
add https://soundcloud.com/forss/flickermood
download https://soundcloud.com/forss/flickermood
updates the weeknd
play https://open.spotify.com/track/2TpxZ7JUBn3uw46aR7qd6V
search youtube aphex twin xtal
search soundcloud lofi hip hop
```
