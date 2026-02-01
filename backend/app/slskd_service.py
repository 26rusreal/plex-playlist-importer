"""
SLSKD Service - API client for Soulseek daemon
Allows searching and downloading tracks from Soulseek P2P network
"""
import os
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import requests

logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "backoff_multiplier": 2,
    "retryable_status_codes": [408, 429, 500, 502, 503, 504]
}

DEFAULT_POLLING_CONFIG = {
    "max_wait_time": 30.0,
    "initial_interval": 0.2,
    "max_interval": 1.0,
    "backoff_multiplier": 1.3
}

# Non-retriable error patterns
NON_RETRIABLE_PATTERNS = [
    'File not shared',
    'Transfer rejected',
    'User is offline',
    'user is not online',
    'not sharing',
    'file not found',
    'access denied'
]


@dataclass
class SlskdSettings:
    """SLSKD configuration settings"""
    enabled: bool = False
    url: str = ""
    allowed_extensions: List[str] = field(default_factory=lambda: ["flac", "mp3", "wav", "ogg", "m4a"])
    search_timeout: int = 10  # seconds
    max_results: int = 50
    download_attempts: int = 3


@dataclass
class SlskdFile:
    """Represents a file from SLSKD search results"""
    username: str
    filename: str
    size: int
    extension: str
    bit_rate: Optional[int] = None
    sample_rate: Optional[int] = None
    bit_depth: Optional[int] = None
    length: Optional[int] = None
    is_locked: bool = False


@dataclass
class SlskdSearchResult:
    """Search result from SLSKD"""
    search_id: str
    query: str
    state: str
    files: List[SlskdFile]
    file_count: int


class SlskdService:
    """Service for interacting with SLSKD API"""
    
    def __init__(self, url: str, api_key: str, settings: Optional[SlskdSettings] = None):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.settings = settings or SlskdSettings()
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
        logger.info(f"SlskdService initialized with URL: {self.url}")
    
    def test_connection(self) -> tuple[bool, str]:
        """Test connection to SLSKD server"""
        try:
            response = self._request_with_retry(
                'GET',
                '/api/v0/application',
                timeout=10
            )
            if response.status_code == 200:
                return True, "Connected successfully to SLSKD"
            return False, f"Unexpected status: {response.status_code}"
        except Exception as e:
            logger.error(f"SLSKD connection test failed: {e}")
            return False, str(e)
    
    def search(self, query: str, timeout: Optional[int] = None) -> SlskdSearchResult:
        """
        Search for tracks on Soulseek network
        
        Args:
            query: Search query (e.g., "Artist - Title")
            timeout: Search timeout in seconds
            
        Returns:
            SlskdSearchResult with found files
        """
        timeout = timeout or self.settings.search_timeout
        
        # Submit search
        search_id = self._submit_search(query, timeout)
        logger.info(f"Search submitted: {search_id} for query: '{query}'")
        
        # Wait for results
        result = self._wait_for_search(search_id, timeout)
        
        return result
    
    def queue_download(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Queue files for download
        
        Args:
            files: List of dicts with username, filename, size
            
        Returns:
            Dict with success status and queued file info
        """
        errors = []
        
        for i, file_info in enumerate(files):
            username = file_info.get('username', '')
            filename = file_info.get('filename', '')
            size = file_info.get('size')
            
            logger.info(f"Trying source {i + 1}/{len(files)}: {username} - {filename}")
            
            try:
                result = self._queue_single_download(username, filename, size)
                if result:
                    logger.info(f"Successfully queued from {username}: {filename}")
                    return {
                        "success": True,
                        "file": file_info,
                        "message": f"Queued from {username}"
                    }
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a non-retriable error
                if any(pattern.lower() in error_str for pattern in NON_RETRIABLE_PATTERNS):
                    logger.info(f"Non-retriable error from {username}, trying next: {e}")
                    errors.append(f"[{i + 1}/{len(files)}] {username}: Source unavailable")
                    continue
                
                # Check for duplicate transfer (treat as success)
                if 'already in progress' in error_str or 'duplicatetransfer' in error_str:
                    logger.info(f"File already queued: {filename}")
                    return {
                        "success": True,
                        "file": file_info,
                        "message": "Already in download queue"
                    }
                
                errors.append(f"[{i + 1}/{len(files)}] {username}: {str(e)}")
        
        return {
            "success": False,
            "file": None,
            "message": f"Failed to queue from {len(files)} source(s): {'; '.join(errors)}"
        }
    
    def _submit_search(self, query: str, timeout: int) -> str:
        """Submit a search request and return search ID"""
        response = self._request_with_retry(
            'POST',
            '/api/v0/searches',
            json={
                "searchText": query,
                "filterResponses": False,
                "maximumPeerQueueLength": 1000000,
                "minimumPeerUploadSpeed": 0,
                "minimumResponseFileCount": 1,
                "responseLimit": 100,
                "timeout": timeout * 1000  # Convert to ms
            }
        )
        
        data = response.json()
        if not data.get('id'):
            raise ValueError("No search ID returned from API")
        
        return data['id']
    
    def _wait_for_search(self, search_id: str, timeout: int) -> SlskdSearchResult:
        """Poll for search completion and return results"""
        config = DEFAULT_POLLING_CONFIG.copy()
        config['max_wait_time'] = timeout * 1000  # Convert to ms
        
        start_time = time.time()
        current_interval = config['initial_interval']
        
        while (time.time() - start_time) < timeout:
            status = self._get_search_status(search_id)
            state = status.get('state', '')
            
            if 'Completed' in state:
                return self._get_search_responses(search_id)
            
            if 'Errored' in state:
                raise ValueError(f"Search {search_id} failed with state: {state}")
            
            if 'Cancelled' in state:
                raise ValueError(f"Search {search_id} was cancelled")
            
            time.sleep(current_interval)
            current_interval = min(
                current_interval * config['backoff_multiplier'],
                config['max_interval']
            )
        
        raise TimeoutError(f"Search {search_id} timed out after {timeout}s")
    
    def _get_search_status(self, search_id: str) -> Dict[str, Any]:
        """Get status of a search"""
        response = self._request_with_retry(
            'GET',
            f'/api/v0/searches/{search_id}'
        )
        return response.json()
    
    def _get_search_responses(self, search_id: str) -> SlskdSearchResult:
        """Get search responses and convert to SlskdSearchResult"""
        response = self._request_with_retry(
            'GET',
            f'/api/v0/searches/{search_id}/responses'
        )
        
        data = response.json()
        user_responses = data if isinstance(data, list) else []
        
        files = []
        for user_response in user_responses:
            username = user_response.get('username', '')
            for file_data in user_response.get('files', []):
                ext = file_data.get('extension', '').lower().lstrip('.')
                
                # Filter by allowed extensions
                if self.settings.allowed_extensions and ext not in self.settings.allowed_extensions:
                    continue
                
                files.append(SlskdFile(
                    username=username,
                    filename=file_data.get('filename', ''),
                    size=file_data.get('size', 0),
                    extension=ext,
                    bit_rate=file_data.get('bitRate'),
                    sample_rate=file_data.get('sampleRate'),
                    bit_depth=file_data.get('bitDepth'),
                    length=file_data.get('length'),
                    is_locked=file_data.get('isLocked', False)
                ))
        
        # Sort by quality (FLAC > WAV > MP3 > others)
        extension_priority = {'flac': 0, 'wav': 1, 'mp3': 2, 'ogg': 3, 'm4a': 4}
        files.sort(key=lambda f: (
            extension_priority.get(f.extension, 99),
            -(f.bit_rate or 0)
        ))
        
        return SlskdSearchResult(
            search_id=search_id,
            query='',
            state='Completed',
            files=files,
            file_count=len(files)
        )
    
    def _queue_single_download(self, username: str, filename: str, size: Optional[int] = None) -> bool:
        """Queue a single file for download"""
        encoded_username = requests.utils.quote(username, safe='')
        
        payload = [{"filename": filename}]
        if size:
            payload[0]["size"] = size
        
        response = self._request_with_retry(
            'POST',
            f'/api/v0/transfers/downloads/{encoded_username}',
            json=payload,
            timeout=10
        )
        
        return response.status_code == 200 or response.status_code == 201
    
    def _request_with_retry(
        self,
        method: str,
        path: str,
        max_retries: int = 3,
        **kwargs
    ) -> requests.Response:
        """Execute request with retry logic"""
        url = f"{self.url}{path}"
        config = DEFAULT_RETRY_CONFIG.copy()
        config['max_retries'] = max_retries
        
        last_error = None
        
        for attempt in range(config['max_retries'] + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Check for retryable status codes
                if response.status_code in config['retryable_status_codes']:
                    raise requests.exceptions.HTTPError(f"Status {response.status_code}")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                last_error = e
                
                if attempt < config['max_retries']:
                    delay = min(
                        config['initial_delay'] * (config['backoff_multiplier'] ** attempt),
                        config['max_delay']
                    )
                    # Add jitter
                    import random
                    delay = delay * (0.75 + random.random() * 0.5)
                    logger.warning(f"Request failed, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                    continue
                
                break
        
        raise last_error or Exception("Request failed")


def get_slskd_api_key() -> str:
    """Get SLSKD API key from environment"""
    return os.environ.get('SLSKD_API_KEY', '')


def is_slskd_configured() -> bool:
    """Check if SLSKD API key is configured"""
    return bool(get_slskd_api_key())


def get_slskd_service() -> Optional[SlskdService]:
    """Get configured SLSKD service instance"""
    from .config import load_settings
    
    api_key = get_slskd_api_key()
    if not api_key:
        return None
    
    settings_data = load_settings()
    
    url = settings_data.get('slskd_url', os.environ.get('SLSKD_URL', 'http://localhost:5030'))
    
    slskd_settings = SlskdSettings(
        enabled=settings_data.get('slskd_enabled', False),
        url=url,
        allowed_extensions=settings_data.get('slskd_allowed_extensions', ['flac', 'mp3', 'wav', 'ogg', 'm4a']),
        search_timeout=settings_data.get('slskd_search_timeout', 10),
        max_results=settings_data.get('slskd_max_results', 50),
        download_attempts=settings_data.get('slskd_download_attempts', 3)
    )
    
    return SlskdService(url, api_key, slskd_settings)
