# Plex Playlist Importer

A modern web application to import playlists into Plex Media Server from M3U files and Spotify.

![Docker Pulls](https://img.shields.io/docker/pulls/26rusreal/plex-playlist-importer)
![License](https://img.shields.io/github/license/26rusreal/plex-playlist-importer)

## Features

- **M3U Import** - Scan folders for M3U/M3U8 playlist files
- **Spotify Import** - Import playlists directly from Spotify URLs (no Spotify account needed)
- **Smart Matching** - Intelligent track matching using title, artist, and filename
- **Progress Visualization** - Real-time import progress with track-by-track status
- **Plex OAuth** - Easy sign-in with your Plex account
- **Batch Import** - Import multiple playlists at once
- **Modern UI** - Dark theme matching Plex aesthetic
- **Docker Ready** - Easy deployment with Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

```yaml
services:
  plex-playlist-importer:
    image: ghcr.io/26rusreal/plex-playlist-importer:latest
    container_name: plex-playlist-importer
    restart: unless-stopped
    ports:
      - "8765:8000"
    volumes:
      - ./config:/config
      - /path/to/your/playlists:/playlists:ro
    environment:
      - TZ=Europe/Moscow
```

```bash
docker compose up -d
```

Open http://localhost:8765

### Using Docker Run

```bash
docker run -d \
  --name plex-playlist-importer \
  -p 8765:8000 \
  -v $(pwd)/config:/config \
  -v /path/to/playlists:/playlists:ro \
  ghcr.io/26rusreal/plex-playlist-importer:latest
```

## Configuration

### 1. Connect to Plex

**Option A: OAuth (Recommended)**
1. Go to Settings
2. Click "Sign in with Plex"
3. Authorize in the popup window
4. Select your server

**Option B: Manual Token**
1. Open Plex Web App → any media item → (...) → Get Info → View XML
2. Copy `X-Plex-Token` from the URL
3. Enter in Settings → Manual Token Entry

### 2. Select Music Library

After connecting, select your music library from the dropdown.

### 3. Spotify Integration (Optional)

For Spotify playlist import, the app can use:

**Option A: External Scraper (Recommended for geo-blocked regions)**

If you have [spotify-to-plex](https://github.com/jjdenhertog/spotify-to-plex) running, the app will automatically detect and use its scraper service.

Add to docker-compose.yml:
```yaml
environment:
  - SPOTIFY_SCRAPER_URL=http://host.docker.internal:3020
extra_hosts:
  - "host.docker.internal:host-gateway"
```

**Option B: Spotify API**

1. Create app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Copy Client ID and Client Secret
3. Enter in Settings → Spotify Integration

## Usage

### Import M3U Playlists

1. Mount your playlists folder to `/playlists` in the container
2. Playlists will appear on the home page
3. Click "Preview" to see track matching
4. Click "Import" to create the playlist in Plex

### Import from Spotify

1. Copy any public Spotify playlist URL
2. Paste into "Import from Spotify" section
3. Click "Preview" to see matched tracks
4. Click "Import to Plex"

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `UTC` |
| `SPOTIFY_SCRAPER_URL` | External Spotify scraper URL | `http://localhost:3020` |

## API Endpoints

### Settings
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings
- `POST /api/test-connection` - Test Plex connection
- `GET /api/libraries` - Get music libraries

### Plex Auth
- `POST /api/auth/start` - Start OAuth flow
- `GET /api/auth/check/{code}` - Check OAuth status
- `POST /api/auth/save` - Save token
- `GET /api/auth/servers` - Get user's servers
- `POST /api/auth/logout` - Logout

### Playlists
- `GET /api/playlists` - List M3U playlists
- `GET /api/playlists/preview` - Preview with matching
- `POST /api/playlists/import` - Import single playlist
- `POST /api/playlists/import-batch` - Batch import

### Spotify
- `GET /api/spotify/status` - Check Spotify availability
- `POST /api/spotify/preview` - Preview Spotify playlist
- `POST /api/spotify/import` - Import Spotify playlist
- `POST /api/spotify/credentials` - Save API credentials

## Development

### Backend (FastAPI + Python)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (Vue.js + Vite)

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

- **Backend**: FastAPI, PlexAPI, Spotipy
- **Frontend**: Vue.js 3, Vite, Axios
- **Container**: Docker, multi-stage build

## Changelog

### v1.2.0
- **Import progress** – Spinning dots indicator in preview modals during import (M3U and Spotify)
- **Status icons** – Green/red rectangular indicators instead of text badges (matched/not found, success/failed)
- **SLSKD (Soulseek)** – Optional integration to search and download missing tracks via SLSKD daemon
- **Recursive playlist scan** – M3U playlists discovered recursively under the music folder; grouping by folder in UI
- **Accessibility** – ARIA labels, Escape to close modals, focus-visible styles, stable list keys
- **Backend** – FastAPI Depends() for Plex service, structured error logging

### v1.1.0
- Progress bar and simplified status icons in preview modals

### v1.0.0
- Initial release: M3U and Spotify import, Plex OAuth, batch import

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [PlexAPI](https://github.com/pkkid/python-plexapi) - Python Plex client
- [spotify-to-plex](https://github.com/jjdenhertog/spotify-to-plex) - Spotify scraper service
