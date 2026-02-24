from plexapi.server import PlexServer
from plexapi.exceptions import NotFound, Unauthorized
from typing import List, Optional, Tuple
from dataclasses import dataclass
import os
import re
import requests
from difflib import SequenceMatcher

# Plex .plex.direct often has hostname mismatch on local IP changes
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

from .m3u_parser import Playlist, Track

logger = __import__("logging").getLogger(__name__)


@dataclass
class MatchResult:
    track: Track
    plex_track: Optional[any] = None
    matched: bool = False
    match_type: str = "none"  # exact, fuzzy, none


@dataclass
class ImportResult:
    playlist_name: str
    total_tracks: int
    matched_tracks: int
    created: bool
    error: Optional[str] = None
    matches: List[MatchResult] = None


class PlexService:
    def __init__(self, url: str, token: str, library_name: str = "Music"):
        self.url = url
        self.token = token
        self.library_name = library_name
        self._server = None
        self._library = None
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to Plex server"""
        try:
            session = requests.Session()
            session.verify = False
            # Ensure session is used for all requests (no default verify)
            adapter = requests.adapters.HTTPAdapter()
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            self._server = PlexServer(
                self.url, self.token, timeout=30, session=session
            )
            return True, f"Connected to {self._server.friendlyName}"
        except Unauthorized:
            return False, "Invalid Plex token"
        except Exception as e:
            logger.exception("Plex connection failed")
            return False, f"Connection failed: {str(e)}"
    
    def get_library(self):
        """Get music library"""
        if not self._server:
            raise Exception("Not connected to Plex")
        
        if self._library is None:
            try:
                self._library = self._server.library.section(self.library_name)
            except NotFound:
                raise Exception(f"Library '{self.library_name}' not found")
        
        return self._library
    
    def get_libraries(self) -> List[dict]:
        """Get all music libraries"""
        if not self._server:
            raise Exception("Not connected to Plex")
        
        libraries = []
        for section in self._server.library.sections():
            if section.type == 'artist':
                libraries.append({
                    "name": section.title,
                    "key": section.key,
                    "type": section.type
                })
        return libraries
    
    def get_existing_playlists(self) -> List[str]:
        """Get list of existing playlist names"""
        if not self._server:
            return []
        return [p.title for p in self._server.playlists()]
    
    def _normalize_string(self, s: str) -> str:
        """Normalize string for matching"""
        if not s:
            return ""
        # Remove special chars, lowercase
        s = re.sub(r'[^\w\s]', '', s.lower())
        # Remove extra spaces
        s = ' '.join(s.split())
        return s
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity"""
        return SequenceMatcher(None, 
                               self._normalize_string(a), 
                               self._normalize_string(b)).ratio()
    
    def _extract_search_terms(self, track: Track) -> Tuple[str, str]:
        """Extract title and artist from track for searching"""
        title = track.title or ""
        artist = track.artist or ""
        
        # If no title/artist, try to parse from filename
        if not title:
            filename = os.path.splitext(track.filename)[0]
            # Remove track number prefix (e.g., "01. ", "01 - ")
            filename = re.sub(r'^\d+[\.\-\s]+\s*', '', filename)
            
            if ' - ' in filename:
                parts = filename.split(' - ', 1)
                artist = artist or parts[0].strip()
                title = parts[1].strip()
            else:
                title = filename
        
        return title, artist
    
    def find_track(self, track: Track) -> MatchResult:
        """Find a track in Plex library using search"""
        library = self.get_library()
        title, artist = self._extract_search_terms(track)
        
        if not title:
            return MatchResult(track=track, matched=False)
        
        # Strategy 1: Search by title
        try:
            # Search tracks by title
            search_results = library.searchTracks(title=title, maxresults=20)
            
            if search_results:
                # If we have artist, try to match both
                if artist:
                    for plex_track in search_results:
                        plex_artist = plex_track.grandparentTitle or ""
                        title_sim = self._similarity(title, plex_track.title)
                        artist_sim = self._similarity(artist, plex_artist)
                        
                        # Good match on both
                        if title_sim > 0.8 and artist_sim > 0.6:
                            return MatchResult(
                                track=track, 
                                plex_track=plex_track, 
                                matched=True, 
                                match_type="exact"
                            )
                    
                    # Try fuzzy match
                    best_match = None
                    best_score = 0
                    for plex_track in search_results:
                        plex_artist = plex_track.grandparentTitle or ""
                        title_sim = self._similarity(title, plex_track.title)
                        artist_sim = self._similarity(artist, plex_artist)
                        score = (title_sim * 0.6) + (artist_sim * 0.4)
                        
                        if score > best_score and score > 0.7:
                            best_score = score
                            best_match = plex_track
                    
                    if best_match:
                        return MatchResult(
                            track=track, 
                            plex_track=best_match, 
                            matched=True, 
                            match_type="fuzzy"
                        )
                else:
                    # No artist, just match by title
                    for plex_track in search_results:
                        title_sim = self._similarity(title, plex_track.title)
                        if title_sim > 0.85:
                            return MatchResult(
                                track=track, 
                                plex_track=plex_track, 
                                matched=True, 
                                match_type="title"
                            )
        except Exception as e:
            logger.warning("Search error for %r: %s", title, e)
        
        # Strategy 2: Search by artist if title search failed
        if artist:
            try:
                # Search tracks by artist name
                search_results = library.searchTracks(title=artist, maxresults=30)
                
                for plex_track in search_results:
                    title_sim = self._similarity(title, plex_track.title)
                    if title_sim > 0.8:
                        return MatchResult(
                            track=track, 
                            plex_track=plex_track, 
                            matched=True, 
                            match_type="fuzzy"
                        )
            except Exception:
                pass
        
        return MatchResult(track=track, matched=False)
    
    def preview_import(self, playlist: Playlist) -> ImportResult:
        """Preview what tracks would be matched"""
        matches = []
        matched_count = 0
        
        for track in playlist.tracks:
            result = self.find_track(track)
            matches.append(result)
            if result.matched:
                matched_count += 1
        
        return ImportResult(
            playlist_name=playlist.name,
            total_tracks=len(playlist.tracks),
            matched_tracks=matched_count,
            created=False,
            matches=matches
        )
    
    def import_playlist(self, playlist: Playlist, overwrite: bool = False) -> ImportResult:
        """Import playlist to Plex"""
        if not self._server:
            return ImportResult(
                playlist_name=playlist.name,
                total_tracks=len(playlist.tracks),
                matched_tracks=0,
                created=False,
                error="Not connected to Plex"
            )
        
        # Check if playlist exists
        existing = self.get_existing_playlists()
        if playlist.name in existing:
            if overwrite:
                # Delete existing
                for p in self._server.playlists():
                    if p.title == playlist.name:
                        p.delete()
                        break
            else:
                return ImportResult(
                    playlist_name=playlist.name,
                    total_tracks=len(playlist.tracks),
                    matched_tracks=0,
                    created=False,
                    error=f"Playlist '{playlist.name}' already exists"
                )
        
        # Find matching tracks
        plex_tracks = []
        matches = []
        
        for track in playlist.tracks:
            result = self.find_track(track)
            matches.append(result)
            if result.matched and result.plex_track:
                plex_tracks.append(result.plex_track)
        
        if not plex_tracks:
            return ImportResult(
                playlist_name=playlist.name,
                total_tracks=len(playlist.tracks),
                matched_tracks=0,
                created=False,
                error="No matching tracks found in Plex library",
                matches=matches
            )
        
        # Create playlist
        try:
            self._server.createPlaylist(playlist.name, items=plex_tracks)
            return ImportResult(
                playlist_name=playlist.name,
                total_tracks=len(playlist.tracks),
                matched_tracks=len(plex_tracks),
                created=True,
                matches=matches
            )
        except Exception as e:
            return ImportResult(
                playlist_name=playlist.name,
                total_tracks=len(playlist.tracks),
                matched_tracks=len(plex_tracks),
                created=False,
                error=str(e),
                matches=matches
            )
