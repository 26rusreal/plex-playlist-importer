from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import os

from .config import get_settings, save_settings, load_settings
from .m3u_parser import scan_playlists, parse_m3u, Playlist, Track
from .plex_service import PlexService
from . import plex_auth
from .spotify_service import SpotifyService, is_spotify_available

app = FastAPI(title="Plex Playlist Importer", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class SettingsModel(BaseModel):
    plex_url: str
    plex_token: str
    music_library_name: str
    playlists_path: str


class ConnectionTest(BaseModel):
    plex_url: str
    plex_token: str


class ImportRequest(BaseModel):
    playlist_path: str
    overwrite: bool = False


class BatchImportRequest(BaseModel):
    playlist_paths: List[str]
    overwrite: bool = False


class TrackInfo(BaseModel):
    filename: str
    title: Optional[str]
    artist: Optional[str]
    matched: bool
    match_type: str
    plex_title: Optional[str] = None
    plex_artist: Optional[str] = None


class PlaylistInfo(BaseModel):
    name: str
    path: str
    folder: str
    track_count: int
    tracks: Optional[List[TrackInfo]] = None


class ImportResultModel(BaseModel):
    playlist_name: str
    total_tracks: int
    matched_tracks: int
    created: bool
    error: Optional[str] = None


# Global plex service cache
_plex_service: Optional[PlexService] = None


def get_plex_service() -> PlexService:
    global _plex_service
    settings = get_settings()
    
    if _plex_service is None or _plex_service.url != settings.plex_url:
        _plex_service = PlexService(
            url=settings.plex_url,
            token=settings.plex_token,
            library_name=settings.music_library_name
        )
        success, msg = _plex_service.connect()
        if not success:
            _plex_service = None
            raise HTTPException(status_code=500, detail=msg)
    
    return _plex_service


# ============ Settings endpoints ============

@app.get("/api/settings")
def get_current_settings():
    """Get current settings"""
    settings = load_settings()
    # Don't expose full token
    if settings.get("plex_token"):
        settings["plex_token_set"] = True
        settings["plex_token"] = "***" + settings["plex_token"][-4:] if len(settings.get("plex_token", "")) > 4 else "****"
    return settings


@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    """Update settings"""
    data = settings.model_dump()
    # Keep existing token if not changed
    if data.get("plex_token", "").startswith("***"):
        existing = load_settings()
        data["plex_token"] = existing.get("plex_token", "")
    
    save_settings(data)
    
    # Reset plex service cache
    global _plex_service
    _plex_service = None
    
    return {"status": "ok", "message": "Settings saved"}


@app.post("/api/test-connection")
def test_connection(conn: ConnectionTest):
    """Test Plex connection"""
    service = PlexService(url=conn.plex_url, token=conn.plex_token)
    success, msg = service.connect()
    
    if success:
        libraries = service.get_libraries()
        return {
            "status": "ok",
            "message": msg,
            "libraries": libraries
        }
    else:
        raise HTTPException(status_code=400, detail=msg)


@app.get("/api/libraries")
def get_libraries():
    """Get available music libraries"""
    try:
        service = get_plex_service()
        return service.get_libraries()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Plex OAuth endpoints ============

# Store pending auth sessions (in production, use Redis or database)
_pending_auth: Dict[str, dict] = {}


@app.post("/api/auth/start")
def start_auth():
    """Start Plex OAuth flow - returns PIN and auth URL"""
    client_id = plex_auth.generate_client_id()
    pin, error = plex_auth.request_pin(client_id)
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Store the pending auth
    _pending_auth[pin.code] = {
        "pin_id": pin.id,
        "client_id": client_id,
        "code": pin.code
    }
    
    return {
        "code": pin.code,
        "pin_id": pin.id,
        "client_id": client_id,
        "auth_url": pin.auth_url
    }


@app.get("/api/auth/check/{code}")
def check_auth(code: str):
    """Check if PIN has been authorized"""
    if code not in _pending_auth:
        raise HTTPException(status_code=404, detail="Auth session not found")
    
    session = _pending_auth[code]
    token, error = plex_auth.check_pin(session["pin_id"], session["client_id"])
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    if token:
        # Get user info
        user, user_error = plex_auth.get_user_info(token, session["client_id"])
        
        # Get available servers
        servers, servers_error = plex_auth.get_servers(token, session["client_id"])
        
        # Clean up pending auth
        del _pending_auth[code]
        
        return {
            "authorized": True,
            "token": token,
            "user": {
                "username": user.username if user else None,
                "email": user.email if user else None,
                "thumb": user.thumb if user else None
            } if user else None,
            "servers": servers,
            "client_id": session["client_id"]
        }
    
    return {"authorized": False}


@app.post("/api/auth/save")
def save_auth_token(data: dict):
    """Save the authenticated token and server to settings"""
    token = data.get("token")
    server_url = data.get("server_url")
    client_id = data.get("client_id")
    
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    # Load existing settings and update
    settings = load_settings()
    settings["plex_token"] = token
    settings["client_id"] = client_id
    
    if server_url:
        settings["plex_url"] = server_url
    
    save_settings(settings)
    
    # Reset plex service cache
    global _plex_service
    _plex_service = None
    
    return {"status": "ok", "message": "Authentication saved"}


@app.get("/api/auth/servers")
def get_servers():
    """Get list of user's Plex servers using saved token"""
    settings = load_settings()
    token = settings.get("plex_token")
    client_id = settings.get("client_id", plex_auth.generate_client_id())
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    servers, error = plex_auth.get_servers(token, client_id)
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    return servers


@app.post("/api/auth/logout")
def logout():
    """Clear authentication"""
    settings = load_settings()
    settings["plex_token"] = ""
    settings.pop("client_id", None)
    save_settings(settings)
    
    global _plex_service
    _plex_service = None
    
    return {"status": "ok", "message": "Logged out"}


# ============ Playlist endpoints ============

@app.get("/api/playlists", response_model=List[PlaylistInfo])
def list_playlists():
    """Scan and list all m3u playlists"""
    settings = get_settings()
    playlists_path = settings.playlists_path
    
    if not os.path.exists(playlists_path):
        raise HTTPException(status_code=404, detail=f"Playlists path not found: {playlists_path}")
    
    playlists = scan_playlists(playlists_path)
    
    return [
        PlaylistInfo(
            name=p.name,
            path=p.path,
            folder=p.folder,
            track_count=len(p.tracks)
        )
        for p in playlists
    ]


@app.get("/api/playlists/preview")
def preview_playlist(path: str):
    """Preview a specific playlist with track matching"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Playlist file not found")
    
    playlist = parse_m3u(path)
    
    try:
        service = get_plex_service()
        result = service.preview_import(playlist)
        
        tracks = []
        for match in result.matches:
            track_info = TrackInfo(
                filename=match.track.filename,
                title=match.track.title,
                artist=match.track.artist,
                matched=match.matched,
                match_type=match.match_type,
                plex_title=match.plex_track.title if match.plex_track else None,
                plex_artist=match.plex_track.grandparentTitle if match.plex_track else None
            )
            tracks.append(track_info)
        
        return PlaylistInfo(
            name=playlist.name,
            path=playlist.path,
            folder=playlist.folder,
            track_count=len(playlist.tracks),
            tracks=tracks
        )
    except HTTPException:
        # Return playlist without matching if Plex not connected
        return PlaylistInfo(
            name=playlist.name,
            path=playlist.path,
            folder=playlist.folder,
            track_count=len(playlist.tracks),
            tracks=[
                TrackInfo(
                    filename=t.filename,
                    title=t.title,
                    artist=t.artist,
                    matched=False,
                    match_type="unknown"
                )
                for t in playlist.tracks
            ]
        )


@app.post("/api/playlists/import", response_model=ImportResultModel)
def import_playlist(request: ImportRequest):
    """Import a playlist to Plex"""
    if not os.path.exists(request.playlist_path):
        raise HTTPException(status_code=404, detail="Playlist file not found")
    
    playlist = parse_m3u(request.playlist_path)
    service = get_plex_service()
    result = service.import_playlist(playlist, overwrite=request.overwrite)
    
    if result.error and not result.created:
        raise HTTPException(status_code=400, detail=result.error)
    
    return ImportResultModel(
        playlist_name=result.playlist_name,
        total_tracks=result.total_tracks,
        matched_tracks=result.matched_tracks,
        created=result.created,
        error=result.error
    )


@app.post("/api/playlists/import-batch")
def import_batch(request: BatchImportRequest):
    """Import multiple playlists"""
    service = get_plex_service()
    results = []
    
    for path in request.playlist_paths:
        if not os.path.exists(path):
            results.append(ImportResultModel(
                playlist_name=os.path.basename(path),
                total_tracks=0,
                matched_tracks=0,
                created=False,
                error="File not found"
            ))
            continue
        
        playlist = parse_m3u(path)
        result = service.import_playlist(playlist, overwrite=request.overwrite)
        
        results.append(ImportResultModel(
            playlist_name=result.playlist_name,
            total_tracks=result.total_tracks,
            matched_tracks=result.matched_tracks,
            created=result.created,
            error=result.error
        ))
    
    return {
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r.created)
    }


@app.get("/api/plex-playlists")
def get_plex_playlists():
    """Get existing Plex playlists"""
    try:
        service = get_plex_service()
        return service.get_existing_playlists()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Spotify endpoints ============

class SpotifyUrlRequest(BaseModel):
    url: str


class SpotifyImportRequest(BaseModel):
    url: str
    overwrite: bool = False


@app.get("/api/spotify/status")
def spotify_status():
    """Check if Spotify functionality is available"""
    return {
        "available": is_spotify_available(),
        "message": "Spotify integration ready" if is_spotify_available() else "spotifyscraper not installed"
    }


@app.post("/api/spotify/preview")
def preview_spotify_playlist(request: SpotifyUrlRequest):
    """Preview a Spotify playlist - get tracks and match with Plex"""
    if not is_spotify_available():
        raise HTTPException(status_code=503, detail="Spotify functionality not available")
    
    try:
        spotify = SpotifyService()
        playlist = spotify.get_playlist(request.url)
        
        # Try to match tracks with Plex
        tracks_info = []
        try:
            plex = get_plex_service()
            for sp_track in playlist.tracks:
                # Search in Plex
                plex_track = plex.find_track(sp_track.artist, sp_track.title)
                tracks_info.append({
                    "title": sp_track.title,
                    "artist": sp_track.artist,
                    "album": sp_track.album,
                    "duration_ms": sp_track.duration_ms,
                    "matched": plex_track is not None,
                    "match_type": "exact" if plex_track else "none",
                    "plex_title": plex_track.title if plex_track else None,
                    "plex_artist": plex_track.grandparentTitle if plex_track else None
                })
        except HTTPException:
            # Plex not connected - return tracks without matching
            for sp_track in playlist.tracks:
                tracks_info.append({
                    "title": sp_track.title,
                    "artist": sp_track.artist,
                    "album": sp_track.album,
                    "duration_ms": sp_track.duration_ms,
                    "matched": False,
                    "match_type": "unknown",
                    "plex_title": None,
                    "plex_artist": None
                })
        
        return {
            "name": playlist.name,
            "description": playlist.description,
            "owner": playlist.owner,
            "url": playlist.url,
            "image_url": playlist.image_url,
            "track_count": len(playlist.tracks),
            "tracks": tracks_info
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching playlist: {str(e)}")


@app.post("/api/spotify/import")
def import_spotify_playlist(request: SpotifyImportRequest):
    """Import a Spotify playlist to Plex"""
    if not is_spotify_available():
        raise HTTPException(status_code=503, detail="Spotify functionality not available")
    
    try:
        spotify = SpotifyService()
        sp_playlist = spotify.get_playlist(request.url)
        
        # Convert to Playlist format for import
        tracks = []
        for sp_track in sp_playlist.tracks:
            track = Track(
                filename=f"{sp_track.artist} - {sp_track.title}",
                path=f"spotify:{sp_track.uri or ''}",
                title=sp_track.title,
                artist=sp_track.artist,
                duration=sp_track.duration_ms // 1000 if sp_track.duration_ms else None
            )
            tracks.append(track)
        
        playlist = Playlist(
            name=sp_playlist.name,
            path=f"spotify:{sp_playlist.url}",
            folder="Spotify",
            tracks=tracks
        )
        
        # Import to Plex
        plex = get_plex_service()
        result = plex.import_playlist(playlist, overwrite=request.overwrite)
        
        return {
            "playlist_name": result.playlist_name,
            "total_tracks": result.total_tracks,
            "matched_tracks": result.matched_tracks,
            "created": result.created,
            "error": result.error,
            "source": "spotify",
            "spotify_url": request.url,
            "matches": [
                {
                    "filename": m.track.filename,
                    "title": m.track.title,
                    "artist": m.track.artist,
                    "matched": m.matched,
                    "match_type": m.match_type,
                    "plex_title": m.plex_track.title if m.plex_track else None,
                    "plex_artist": m.plex_track.grandparentTitle if m.plex_track else None
                }
                for m in result.matches
            ] if hasattr(result, 'matches') else []
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# ============ Static files (frontend) ============

# Mount static files if frontend build exists
frontend_path = "/app/frontend/dist"
if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=f"{frontend_path}/assets"), name="assets")
    
    @app.get("/")
    def serve_frontend():
        return FileResponse(f"{frontend_path}/index.html")
    
    @app.get("/playlist-icon.png")
    def serve_icon():
        return FileResponse(f"{frontend_path}/playlist-icon.png")
    
    @app.get("/{path:path}")
    def serve_frontend_routes(path: str):
        # Serve index.html for all non-API routes (SPA routing)
        if not path.startswith("api/"):
            # Check if it's a static file that exists
            static_path = f"{frontend_path}/{path}"
            if os.path.isfile(static_path):
                return FileResponse(static_path)
            return FileResponse(f"{frontend_path}/index.html")
