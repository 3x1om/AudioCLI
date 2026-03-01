# audiocli

Linux-only terminal music player that resolves user queries/links and plays audio with `mpv`.

Supported flow:
- YouTube links + search
- SoundCloud links + search
- Spotify links (resolved to playable audio by searching for the same track)
- Many other sites supported by `yt-dlp` links

## Important notes
- Spotify streams are DRM-protected; this app does **not** play Spotify streams directly.
- For Spotify links, the app fetches track metadata and resolves to a playable source.
- The app itself does not inject ads.

## Requirements (Linux)
- `python >= 3.11`
- `mpv`
- internet connection

## One-line install + run (Fedora)

```bash
git clone https://github.com/3x1om/audiocli.git && cd audiocli && sudo dnf install -y mpv ffmpeg python3 python3-pip && python3 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -e . && audiocli
```

## Manual install

```bash
sudo dnf install -y mpv ffmpeg python3 python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Optional Spotify search support:

```bash
pip install -e .[spotify]
export SPOTIFY_CLIENT_ID="..."
export SPOTIFY_CLIENT_SECRET="..."
```

## Run

```bash
audiocli
# or
python -m audiocli
```

## Commands

```text
play <query_or_url>      resolve and play immediately
add <query_or_url>       resolve and add to queue
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
add https://soundcloud.com/forss/flickermood
play https://open.spotify.com/track/2TpxZ7JUBn3uw46aR7qd6V
search youtube aphex twin xtal
search soundcloud lofi hip hop
```
