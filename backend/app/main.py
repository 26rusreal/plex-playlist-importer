from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
import os

logger = logging.getLogger(__name__)

from .config import get_settings, save_settings, load_settings
from .m3u_parser import scan_playlists, parse_m3u, Playlist, Track
from .plex_service import PlexService
from . import plex_auth
from .spotify_service import SpotifyService, is_spotify_available, is_spotify_configured, get_spotify_service

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
    group: Optional[str] = None  # first folder under music root, e.g. "Artists", "Spotify Playlists"
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
            logger.warning("Plex connection failed: %s", msg)
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
    """Update settings (merge with existing so Spotify/SLSKD etc. are not lost)"""
    existing = load_settings()
    data = settings.model_dump()
    # Keep existing token if not changed
    if data.get("plex_token", "").startswith("***"):
        data["plex_token"] = existing.get("plex_token", "")
    # Merge: keep all keys not in SettingsModel (spotify_*, slskd_*, client_id)
    for key in list(existing.keys()):
        if key not in data:
            data[key] = existing[key]
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
def get_libraries(service: PlexService = Depends(get_plex_service)):
    """Get available music libraries"""
    try:
        return service.get_libraries()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get libraries")
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
        raise HTTPException(
            status_code=404,
            detail=f"Path not found: {playlists_path}. Mount your music root in Docker (e.g. -v /host/music:/music) and set this to /music."
        )
    
    playlists = scan_playlists(playlists_path)
    root = os.path.normpath(playlists_path)

    result = []
    for p in playlists:
        try:
            rel = os.path.relpath(os.path.normpath(p.folder), root)
            if not rel or rel == "." or rel == "..":
                group = "Root"
            else:
                group = rel.split(os.sep)[0] if os.sep in rel else rel
        except ValueError:
            group = "Root"
        result.append(
            PlaylistInfo(
                name=p.name,
                path=p.path,
                folder=p.folder,
                track_count=len(p.tracks),
                group=group,
            )
        )
    return result


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
        
        # #region agent log
        _resp = PlaylistInfo(name=playlist.name, path=playlist.path, folder=playlist.folder, track_count=len(playlist.tracks), tracks=tracks)
        try:
            _log = {"hypothesisId":"H1","location":"main.py:preview_playlist","message":"preview response","data":{"keys":list(_resp.model_dump().keys()),"tracks_len":len(tracks),"tracks_type":type(_resp.tracks).__name__},"timestamp":__import__("time").time()*1000}
            open("/cursor-debug/debug-459f84.log", "a").write(__import__("json").dumps(_log) + "\n")
        except Exception:
            pass
        return _resp
        # #endregion
    except HTTPException:
        # Return playlist without matching if Plex not connected
        fallback_tracks = [
            TrackInfo(filename=t.filename, title=t.title, artist=t.artist, matched=False, match_type="unknown")
            for t in playlist.tracks
        ]
        res_fallback = PlaylistInfo(name=playlist.name, path=playlist.path, folder=playlist.folder, track_count=len(playlist.tracks), tracks=fallback_tracks)
        # #region agent log
        try:
            _log = {"hypothesisId":"H1","location":"main.py:preview_playlist_fallback","message":"preview fallback","data":{"tracks_len":len(fallback_tracks)},"timestamp":__import__("time").time()*1000}
            open("/cursor-debug/debug-459f84.log", "a").write(__import__("json").dumps(_log) + "\n")
        except Exception:
            pass
        return res_fallback
        # #endregion


@app.post("/api/playlists/import", response_model=ImportResultModel)
def import_playlist(request: ImportRequest, service: PlexService = Depends(get_plex_service)):
    """Import a playlist to Plex"""
    if not os.path.exists(request.playlist_path):
        raise HTTPException(status_code=404, detail="Playlist file not found")
    
    playlist = parse_m3u(request.playlist_path)
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
def import_batch(request: BatchImportRequest, service: PlexService = Depends(get_plex_service)):
    """Import multiple playlists"""
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
def get_plex_playlists(service: PlexService = Depends(get_plex_service)):
    """Get existing Plex playlists"""
    try:
        return service.get_existing_playlists()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get Plex playlists")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Spotify endpoints ============

class SpotifyUrlRequest(BaseModel):
    url: str


class SpotifyImportRequest(BaseModel):
    url: str
    overwrite: bool = False


class SpotifyCredentials(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/spotify/status")
def spotify_status():
    """Check if Spotify functionality is available and configured"""
    available = is_spotify_available()
    configured = is_spotify_configured() if available else False
    
    if not available:
        message = "spotipy not installed"
    elif not configured:
        message = "Spotify credentials not configured. Add Client ID and Secret in Settings."
    else:
        message = "Spotify integration ready"
    
    return {
        "available": available,
        "configured": configured,
        "message": message
    }


@app.post("/api/spotify/credentials")
def save_spotify_credentials(creds: SpotifyCredentials):
    """Save Spotify API credentials"""
    settings = load_settings()
    settings["spotify_client_id"] = creds.client_id
    settings["spotify_client_secret"] = creds.client_secret
    save_settings(settings)
    return {"status": "ok", "message": "Spotify credentials saved"}


@app.get("/api/spotify/credentials")
def get_spotify_credentials():
    """Get Spotify credentials (masked)"""
    settings = load_settings()
    client_id = settings.get("spotify_client_id", "")
    client_secret = settings.get("spotify_client_secret", "")
    return {
        "client_id": client_id[:8] + "..." if len(client_id) > 8 else client_id,
        "client_secret": "***" + client_secret[-4:] if len(client_secret) > 4 else "****" if client_secret else "",
        "configured": bool(client_id and client_secret)
    }


@app.post("/api/spotify/preview")
def preview_spotify_playlist(request: SpotifyUrlRequest):
    """Preview a Spotify playlist - get tracks and match with Plex"""
    if not is_spotify_available():
        raise HTTPException(status_code=503, detail="Spotify functionality not available")
    
    if not is_spotify_configured():
        raise HTTPException(status_code=400, detail="Spotify credentials not configured. Go to Settings to add Client ID and Secret.")
    
    try:
        spotify = get_spotify_service()
        playlist = spotify.get_playlist(request.url)
        
        # Try to match tracks with Plex
        tracks_info = []
        try:
            plex = get_plex_service()
            for sp_track in playlist.tracks:
                # Create Track object for matching
                track_obj = Track(
                    filename=f"{sp_track.artist} - {sp_track.title}",
                    path="",
                    title=sp_track.title,
                    artist=sp_track.artist
                )
                # Search in Plex
                match_result = plex.find_track(track_obj)
                plex_track = match_result.plex_track if match_result.matched else None
                tracks_info.append({
                    "title": sp_track.title,
                    "artist": sp_track.artist,
                    "album": sp_track.album,
                    "duration_ms": sp_track.duration_ms,
                    "matched": match_result.matched,
                    "match_type": match_result.match_type,
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
        logger.exception("Error fetching Spotify playlist")
        raise HTTPException(status_code=500, detail=f"Error fetching playlist: {str(e)}")


@app.post("/api/spotify/import")
def import_spotify_playlist(
    request: SpotifyImportRequest,
    plex: PlexService = Depends(get_plex_service),
):
    """Import a Spotify playlist to Plex"""
    if not is_spotify_available():
        raise HTTPException(status_code=503, detail="Spotify functionality not available")
    
    if not is_spotify_configured():
        raise HTTPException(status_code=400, detail="Spotify credentials not configured")
    
    try:
        spotify = get_spotify_service()
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
        logger.exception("Spotify import failed")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# ============ SLSKD endpoints ============

from .slskd_service import (
    is_slskd_configured, get_slskd_service, get_slskd_api_key,
    SlskdSettings as SlskdSettingsModel
)


class SlskdSettingsRequest(BaseModel):
    enabled: bool = False
    url: str = ""
    allowed_extensions: List[str] = ["flac", "mp3", "wav", "ogg", "m4a"]
    search_timeout: int = 10
    max_results: int = 50
    download_attempts: int = 3


class SlskdSearchRequest(BaseModel):
    query: str
    artist: Optional[str] = None
    title: Optional[str] = None


class SlskdQueueRequest(BaseModel):
    files: List[dict]


@app.get("/api/slskd/status")
def slskd_status():
    """Check if SLSKD is available and configured"""
    api_key_set = is_slskd_configured()
    settings = load_settings()
    enabled = settings.get('slskd_enabled', False)
    
    return {
        "available": api_key_set,
        "enabled": enabled and api_key_set,
        "message": "SLSKD ready" if api_key_set and enabled else (
            "SLSKD API key not set" if not api_key_set else "SLSKD disabled"
        )
    }


@app.get("/api/slskd/settings")
def get_slskd_settings():
    """Get SLSKD settings"""
    settings = load_settings()
    return {
        "enabled": settings.get('slskd_enabled', False),
        "url": settings.get('slskd_url', 'http://localhost:5030'),
        "allowed_extensions": settings.get('slskd_allowed_extensions', ['flac', 'mp3', 'wav', 'ogg', 'm4a']),
        "search_timeout": settings.get('slskd_search_timeout', 10),
        "max_results": settings.get('slskd_max_results', 50),
        "download_attempts": settings.get('slskd_download_attempts', 3)
    }


@app.post("/api/slskd/settings")
def save_slskd_settings(request: SlskdSettingsRequest):
    """Save SLSKD settings"""
    settings = load_settings()
    settings['slskd_enabled'] = request.enabled
    settings['slskd_url'] = request.url
    settings['slskd_allowed_extensions'] = request.allowed_extensions
    settings['slskd_search_timeout'] = request.search_timeout
    settings['slskd_max_results'] = request.max_results
    settings['slskd_download_attempts'] = request.download_attempts
    save_settings(settings)
    return {"status": "ok", "message": "SLSKD settings saved"}


@app.post("/api/slskd/test")
def test_slskd_connection(data: dict):
    """Test connection to SLSKD server"""
    if not is_slskd_configured():
        raise HTTPException(status_code=400, detail="SLSKD API key not configured")
    
    url = data.get('url', '')
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    from .slskd_service import SlskdService
    service = SlskdService(url, get_slskd_api_key())
    success, message = service.test_connection()
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@app.post("/api/slskd/search")
def slskd_search(request: SlskdSearchRequest):
    """Search for tracks on Soulseek"""
    if not is_slskd_configured():
        raise HTTPException(status_code=400, detail="SLSKD API key not configured")
    
    service = get_slskd_service()
    if not service:
        raise HTTPException(status_code=500, detail="Failed to initialize SLSKD service")
    
    # Build search query
    if request.artist and request.title:
        query = f"{request.artist} {request.title}"
    else:
        query = request.query
    
    try:
        result = service.search(query)
        return {
            "search_id": result.search_id,
            "query": query,
            "file_count": result.file_count,
            "files": [
                {
                    "username": f.username,
                    "filename": f.filename,
                    "size": f.size,
                    "extension": f.extension,
                    "bit_rate": f.bit_rate,
                    "bit_depth": f.bit_depth,
                    "length": f.length
                }
                for f in result.files[:50]  # Limit to 50 results
            ]
        }
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        logger.exception("SLSKD search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/slskd/queue")
def slskd_queue_download(request: SlskdQueueRequest):
    """Queue files for download"""
    if not is_slskd_configured():
        raise HTTPException(status_code=400, detail="SLSKD API key not configured")
    
    service = get_slskd_service()
    if not service:
        raise HTTPException(status_code=500, detail="Failed to initialize SLSKD service")
    
    try:
        result = service.queue_download(request.files)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['message'])
    except Exception as e:
        logger.exception("SLSKD queue failed")
        raise HTTPException(status_code=500, detail=f"Queue failed: {str(e)}")


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
