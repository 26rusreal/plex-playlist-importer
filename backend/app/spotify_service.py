"""
Spotify Playlist Service - через внешний scraper или официальный API
"""
from typing import Optional, List
from urllib.parse import urlparse
import logging
import os
import requests
from dataclasses import dataclass

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Scraper service URL (spotify-to-plex scraper)
SCRAPER_URL = os.environ.get('SPOTIFY_SCRAPER_URL', 'http://localhost:3020')


@dataclass
class SpotifyTrack:
    """Трек из Spotify плейлиста"""
    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    uri: Optional[str] = None


@dataclass
class SpotifyPlaylist:
    """Spotify плейлист"""
    name: str
    description: Optional[str]
    owner: str
    url: str
    tracks: List[SpotifyTrack]
    image_url: Optional[str] = None
    total_tracks: int = 0


class SpotifyScraperService:
    """Сервис для работы со Spotify через внешний scraper (обход гео-блокировок)"""
    
    def __init__(self, scraper_url: str = None):
        self.scraper_url = scraper_url or SCRAPER_URL
        logger.info(f"SpotifyScraperService initialized with {self.scraper_url}")
    
    def get_playlist(self, url: str) -> SpotifyPlaylist:
        """Получение плейлиста через scraper сервис"""
        if not SpotifyService.is_valid_url(url):
            raise ValueError("Невалидный Spotify URL")
        
        try:
            logger.info(f"Fetching playlist via scraper: {url}")
            
            response = requests.post(
                f"{self.scraper_url}/playlist",
                json={"url": url, "include_album_data": False},
                timeout=120
            )
            
            if response.status_code != 200:
                raise ValueError(f"Scraper error: {response.status_code}")
            
            data = response.json()
            
            tracks = []
            for track_data in data.get('tracks', []):
                artists = track_data.get('artists', [])
                artist_name = artists[0].get('name', 'Unknown') if artists else 'Unknown'
                
                track = SpotifyTrack(
                    title=track_data.get('name', 'Unknown'),
                    artist=artist_name,
                    album=track_data.get('album', {}).get('name') if isinstance(track_data.get('album'), dict) else None,
                    duration_ms=track_data.get('duration_ms'),
                    uri=track_data.get('uri')
                )
                tracks.append(track)
            
            images = data.get('images', [])
            image_url = None
            for img in images:
                if isinstance(img, dict) and img.get('height', 0) >= 300:
                    image_url = img.get('url')
                    break
            if not image_url and images:
                image_url = images[0].get('url') if isinstance(images[0], dict) else None
            
            playlist = SpotifyPlaylist(
                name=data.get('name', 'Unknown Playlist'),
                description=data.get('description'),
                owner=data.get('owner', {}).get('name', 'Unknown') if isinstance(data.get('owner'), dict) else 'Unknown',
                url=url,
                tracks=tracks,
                image_url=image_url,
                total_tracks=data.get('track_count', len(tracks))
            )
            
            logger.info(f"Successfully fetched playlist: {playlist.name} ({len(tracks)} tracks)")
            return playlist
            
        except requests.exceptions.Timeout:
            raise ValueError("Scraper timeout - плейлист слишком большой или сервис недоступен")
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            raise ValueError(f"Ошибка scraper: {str(e)}")


class SpotifyService:
    """Сервис для работы со Spotify API (может быть заблокирован в некоторых странах)"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        if not SPOTIPY_AVAILABLE:
            raise ImportError("spotipy не установлен")
        
        self.client_id = client_id or os.environ.get('SPOTIFY_CLIENT_ID', '')
        self.client_secret = client_secret or os.environ.get('SPOTIFY_CLIENT_SECRET', '')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials not configured")
        
        auth_manager = SpotifyClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.client = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("SpotifyService initialized with API credentials")
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Проверка валидности Spotify URL"""
        try:
            parsed = urlparse(url)
            if parsed.netloc not in ['open.spotify.com', 'spotify.com']:
                return False
            path_parts = parsed.path.strip('/').split('/')
            return len(path_parts) >= 2 and path_parts[0] == 'playlist'
        except Exception:
            return False
    
    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        """Извлечение ID плейлиста из URL"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'playlist':
                # Remove query params
                return path_parts[1].split('?')[0]
        except Exception:
            pass
        return None
    
    def get_playlist(self, url: str) -> SpotifyPlaylist:
        """
        Получение плейлиста по URL через Spotify API
        
        Args:
            url: URL Spotify плейлиста
            
        Returns:
            SpotifyPlaylist с треками
        """
        if not self.is_valid_url(url):
            raise ValueError("Невалидный Spotify URL")
        
        playlist_id = self.extract_playlist_id(url)
        if not playlist_id:
            raise ValueError("Не удалось извлечь ID плейлиста")
        
        try:
            logger.info(f"Fetching playlist: {playlist_id}")
            
            # Get playlist info
            playlist_data = self.client.playlist(playlist_id)
            
            # Get all tracks (handle pagination)
            tracks = []
            results = playlist_data['tracks']
            
            while True:
                for item in results['items']:
                    track_data = item.get('track')
                    if not track_data:
                        continue
                    
                    # Extract artist names
                    artists = track_data.get('artists', [])
                    artist_name = artists[0]['name'] if artists else 'Unknown Artist'
                    
                    track = SpotifyTrack(
                        title=track_data.get('name', 'Unknown'),
                        artist=artist_name,
                        album=track_data.get('album', {}).get('name'),
                        duration_ms=track_data.get('duration_ms'),
                        uri=track_data.get('uri')
                    )
                    tracks.append(track)
                
                # Check for more pages
                if results['next']:
                    results = self.client.next(results)
                else:
                    break
            
            # Extract image
            images = playlist_data.get('images', [])
            image_url = images[0]['url'] if images else None
            
            playlist = SpotifyPlaylist(
                name=playlist_data.get('name', 'Unknown Playlist'),
                description=playlist_data.get('description'),
                owner=playlist_data.get('owner', {}).get('display_name', 'Unknown'),
                url=url,
                tracks=tracks,
                image_url=image_url,
                total_tracks=playlist_data.get('tracks', {}).get('total', len(tracks))
            )
            
            logger.info(f"Successfully fetched playlist: {playlist.name} ({len(tracks)} tracks)")
            return playlist
            
        except Exception as e:
            logger.error(f"Error fetching playlist: {e}")
            raise ValueError(f"Ошибка при получении плейлиста: {str(e)}")


def is_scraper_available() -> bool:
    """Проверка доступности Spotify scraper сервиса"""
    try:
        response = requests.get(f"{SCRAPER_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def is_spotify_available() -> bool:
    """Проверка доступности Spotify функционала (scraper или API)"""
    return is_scraper_available() or SPOTIPY_AVAILABLE


def is_spotify_configured() -> bool:
    """Проверка настроены ли Spotify (scraper доступен или API credentials)"""
    if is_scraper_available():
        return True
    from .config import load_settings
    settings = load_settings()
    client_id = settings.get('spotify_client_id', '')
    client_secret = settings.get('spotify_client_secret', '')
    return bool(client_id and client_secret)


def get_spotify_service():
    """Получение Spotify сервиса (предпочитаем scraper для обхода гео-блокировок)"""
    # Сначала пробуем scraper (обходит гео-блокировки)
    if is_scraper_available():
        return SpotifyScraperService()
    
    # Fallback на прямой API
    from .config import load_settings
    settings = load_settings()
    return SpotifyService(
        client_id=settings.get('spotify_client_id', ''),
        client_secret=settings.get('spotify_client_secret', '')
    )
