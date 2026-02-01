"""
Spotify Playlist Service - парсинг публичных плейлистов без авторизации
"""
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import logging
from dataclasses import dataclass

try:
    from spotify_scraper import SpotifyClient
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False

logger = logging.getLogger(__name__)


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


class SpotifyService:
    """Сервис для работы со Spotify плейлистами"""
    
    def __init__(self):
        if not SPOTIFY_AVAILABLE:
            raise ImportError("spotifyscraper не установлен")
        self.client = SpotifyClient()
        logger.info("SpotifyService initialized")
    
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
                return path_parts[1].split('?')[0]
        except Exception:
            pass
        return None
    
    def get_playlist(self, url: str) -> SpotifyPlaylist:
        """
        Получение плейлиста по URL
        
        Args:
            url: URL Spotify плейлиста
            
        Returns:
            SpotifyPlaylist с треками
        """
        if not self.is_valid_url(url):
            raise ValueError("Невалидный Spotify URL")
        
        try:
            logger.info(f"Scraping playlist: {url}")
            raw_data = self.client.get_playlist_info(url)
            
            if not raw_data:
                raise ValueError("Не удалось получить данные плейлиста")
            
            tracks = []
            raw_tracks = raw_data.get('tracks', [])
            
            for track_data in raw_tracks:
                # Извлекаем информацию о треке
                track = SpotifyTrack(
                    title=track_data.get('name', 'Unknown'),
                    artist=self._extract_artist(track_data),
                    album=track_data.get('album', {}).get('name') if isinstance(track_data.get('album'), dict) else None,
                    duration_ms=track_data.get('duration_ms'),
                    uri=track_data.get('uri')
                )
                tracks.append(track)
            
            playlist = SpotifyPlaylist(
                name=raw_data.get('name', 'Unknown Playlist'),
                description=raw_data.get('description'),
                owner=raw_data.get('owner', {}).get('name', 'Unknown') if isinstance(raw_data.get('owner'), dict) else 'Unknown',
                url=url,
                tracks=tracks,
                image_url=self._extract_image(raw_data)
            )
            
            logger.info(f"Successfully scraped playlist: {playlist.name} ({len(tracks)} tracks)")
            return playlist
            
        except Exception as e:
            logger.error(f"Error scraping playlist: {e}")
            raise ValueError(f"Ошибка при получении плейлиста: {str(e)}")
    
    def _extract_artist(self, track_data: Dict[str, Any]) -> str:
        """Извлечение имени артиста из данных трека"""
        artists = track_data.get('artists', [])
        if isinstance(artists, list) and len(artists) > 0:
            first_artist = artists[0]
            if isinstance(first_artist, dict):
                return first_artist.get('name', 'Unknown Artist')
            elif isinstance(first_artist, str):
                return first_artist
        return 'Unknown Artist'
    
    def _extract_image(self, data: Dict[str, Any]) -> Optional[str]:
        """Извлечение URL изображения"""
        images = data.get('images', [])
        if isinstance(images, list) and len(images) > 0:
            first_image = images[0]
            if isinstance(first_image, dict):
                return first_image.get('url')
            elif isinstance(first_image, str):
                return first_image
        return None


def is_spotify_available() -> bool:
    """Проверка доступности Spotify функционала"""
    return SPOTIFY_AVAILABLE
