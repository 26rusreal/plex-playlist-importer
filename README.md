# Plex Playlist Importer

Web application to import M3U playlists into Plex Media Server.

## Features

- Scan folders for M3U/M3U8 playlist files
- Preview track matching before import
- Smart track matching (filename, title+artist)
- Batch import multiple playlists
- Modern dark UI (Plex-style)
- Docker deployment

## Quick Start

1. **Configure docker-compose.yml:**
   
   Edit the volume mount to point to your playlists folder:
   ```yaml
   volumes:
     - /path/to/your/playlists:/playlists:ro
   ```

2. **Start the container:**
   ```bash
   docker-compose up -d
   ```

3. **Open web UI:**
   
   Go to http://localhost:8765

4. **Configure Plex connection:**
   - Plex URL (e.g., `http://your-plex-ip:32400`)
   - Plex Token (see below how to get it)
   - Music Library name

## Getting Plex Token

1. Open Plex Web App and sign in
2. Browse to any media item
3. Click the three dots (...) menu and select "Get Info"
4. Click "View XML" at the bottom
5. In the URL, find the `X-Plex-Token=` parameter
6. Copy the token value

## Configuration

Settings are stored in `./config/settings.json` and persist across container restarts.

### Environment Variables

- `TZ` - Timezone (default: UTC)

### Docker Network

If your Plex server runs in Docker, make sure both containers are on the same network:

```yaml
services:
  plex-playlist-importer:
    networks:
      - plex_network

networks:
  plex_network:
    external: true
```

## Development

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (Vue.js)

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings
- `POST /api/test-connection` - Test Plex connection
- `GET /api/libraries` - Get Plex music libraries
- `GET /api/playlists` - List all M3U playlists
- `GET /api/playlists/preview?path=...` - Preview playlist with matching
- `POST /api/playlists/import` - Import single playlist
- `POST /api/playlists/import-batch` - Import multiple playlists

## License

MIT
