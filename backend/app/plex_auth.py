"""
Plex OAuth Authentication Module

Implements Plex's PIN-based authentication flow:
1. Request a PIN from Plex
2. User authorizes the app on Plex's website
3. Poll for the auth token using the PIN
"""

import requests
import time
from typing import Optional, Tuple
from dataclasses import dataclass
import uuid

# Plex API endpoints
PLEX_PINS_URL = "https://plex.tv/api/v2/pins"
PLEX_AUTH_URL = "https://app.plex.tv/auth"
PLEX_USER_URL = "https://plex.tv/api/v2/user"

# App identification (you can customize these)
APP_NAME = "Plex Playlist Importer"
APP_ID = "plex-playlist-importer"
APP_VERSION = "1.0.0"

# Headers for Plex API
def get_headers(client_id: str, token: Optional[str] = None) -> dict:
    headers = {
        "Accept": "application/json",
        "X-Plex-Product": APP_NAME,
        "X-Plex-Version": APP_VERSION,
        "X-Plex-Client-Identifier": client_id,
        "X-Plex-Platform": "Web",
        "X-Plex-Platform-Version": "1.0",
        "X-Plex-Device": "Browser",
        "X-Plex-Device-Name": APP_NAME,
    }
    if token:
        headers["X-Plex-Token"] = token
    return headers


@dataclass
class PlexPin:
    id: int
    code: str
    client_id: str
    auth_url: str
    expires_at: str


@dataclass
class PlexUser:
    id: int
    username: str
    email: str
    thumb: str
    token: str


def generate_client_id() -> str:
    """Generate a unique client identifier"""
    return str(uuid.uuid4())


def request_pin(client_id: str) -> Tuple[Optional[PlexPin], Optional[str]]:
    """
    Request a new PIN from Plex for authentication.
    Returns (PlexPin, None) on success or (None, error_message) on failure.
    """
    try:
        response = requests.post(
            PLEX_PINS_URL,
            headers=get_headers(client_id),
            data={"strong": "true"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Build the auth URL
        auth_url = (
            f"{PLEX_AUTH_URL}#?"
            f"clientID={client_id}&"
            f"code={data['code']}&"
            f"context%5Bdevice%5D%5Bproduct%5D={APP_NAME.replace(' ', '%20')}"
        )
        
        return PlexPin(
            id=data["id"],
            code=data["code"],
            client_id=client_id,
            auth_url=auth_url,
            expires_at=data.get("expiresAt", "")
        ), None
        
    except requests.RequestException as e:
        return None, f"Failed to request PIN: {str(e)}"
    except (KeyError, ValueError) as e:
        return None, f"Invalid response from Plex: {str(e)}"


def check_pin(pin_id: int, client_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Check if the PIN has been authorized.
    Returns (token, None) if authorized, (None, None) if pending, (None, error) on failure.
    """
    try:
        response = requests.get(
            f"{PLEX_PINS_URL}/{pin_id}",
            headers=get_headers(client_id),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        auth_token = data.get("authToken")
        if auth_token:
            return auth_token, None
        
        # Not yet authorized
        return None, None
        
    except requests.RequestException as e:
        return None, f"Failed to check PIN: {str(e)}"


def poll_for_token(pin_id: int, client_id: str, timeout: int = 120, interval: int = 2) -> Tuple[Optional[str], Optional[str]]:
    """
    Poll for token until authorized or timeout.
    Returns (token, None) on success or (None, error_message) on failure/timeout.
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        token, error = check_pin(pin_id, client_id)
        
        if error:
            return None, error
        
        if token:
            return token, None
        
        time.sleep(interval)
    
    return None, "Authorization timed out. Please try again."


def get_user_info(token: str, client_id: str) -> Tuple[Optional[PlexUser], Optional[str]]:
    """
    Get user information using the auth token.
    Returns (PlexUser, None) on success or (None, error_message) on failure.
    """
    try:
        response = requests.get(
            PLEX_USER_URL,
            headers=get_headers(client_id, token),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        return PlexUser(
            id=data.get("id", 0),
            username=data.get("username", ""),
            email=data.get("email", ""),
            thumb=data.get("thumb", ""),
            token=token
        ), None
        
    except requests.RequestException as e:
        return None, f"Failed to get user info: {str(e)}"


def get_servers(token: str, client_id: str) -> Tuple[list, Optional[str]]:
    """
    Get list of Plex servers the user has access to.
    Returns (servers_list, None) on success or ([], error_message) on failure.
    """
    try:
        response = requests.get(
            "https://plex.tv/api/v2/resources",
            headers=get_headers(client_id, token),
            params={"includeHttps": 1, "includeRelay": 0},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        servers = []
        for resource in data:
            if resource.get("provides") == "server":
                # Get the best connection (prefer local)
                connections = resource.get("connections", [])
                local_conn = next((c for c in connections if c.get("local")), None)
                remote_conn = next((c for c in connections if not c.get("local")), None)
                
                best_conn = local_conn or remote_conn
                if best_conn:
                    servers.append({
                        "name": resource.get("name", "Unknown"),
                        "clientIdentifier": resource.get("clientIdentifier", ""),
                        "owned": resource.get("owned", False),
                        "url": best_conn.get("uri", ""),
                        "local": best_conn.get("local", False),
                        "accessToken": resource.get("accessToken", token),
                    })
        
        return servers, None
        
    except requests.RequestException as e:
        return [], f"Failed to get servers: {str(e)}"
