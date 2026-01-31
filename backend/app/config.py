from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
import json

CONFIG_FILE = "/config/settings.json"


class Settings(BaseSettings):
    plex_url: str = Field(default="http://localhost:32400")
    plex_token: str = Field(default="")
    music_library_name: str = Field(default="Music")
    playlists_path: str = Field(default="/playlists")
    
    class Config:
        env_prefix = "PLEX_"


def load_settings() -> dict:
    """Load settings from config file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_settings(settings: dict):
    """Save settings to config file"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_settings() -> Settings:
    """Get settings with file overrides"""
    file_settings = load_settings()
    return Settings(**file_settings)
