import os
import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Track:
    filename: str
    path: str
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class Playlist:
    name: str
    path: str
    tracks: List[Track]
    folder: str


def parse_m3u(m3u_path: str) -> Playlist:
    """Parse an m3u file and return playlist info"""
    tracks = []
    current_title = None
    current_artist = None
    current_duration = None
    
    folder = os.path.dirname(m3u_path)
    playlist_name = os.path.basename(folder)
    
    # Try to get name from m3u filename
    m3u_name = os.path.splitext(os.path.basename(m3u_path))[0]
    # Remove emoji prefixes if present
    m3u_name_clean = re.sub(r'^[^\w\s]+\s*', '', m3u_name).strip()
    if m3u_name_clean:
        playlist_name = m3u_name_clean
    
    with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            
            if not line or line.startswith('#EXTM3U') or line.startswith('#EXTIMG'):
                continue
            
            if line.startswith('#EXTINF:'):
                # Parse extended info: #EXTINF:duration,Artist - Title or #EXTINF:duration,Title
                match = re.match(r'#EXTINF:(-?\d+),(.+)', line)
                if match:
                    current_duration = int(match.group(1)) if match.group(1) != '-1' else None
                    info = match.group(2).strip()
                    if ' - ' in info:
                        parts = info.split(' - ', 1)
                        current_artist = parts[0].strip()
                        current_title = parts[1].strip()
                    else:
                        current_title = info
                continue
            
            if not line.startswith('#'):
                # This is a track path
                # Handle relative paths
                if not os.path.isabs(line):
                    track_path = os.path.normpath(os.path.join(folder, line))
                else:
                    track_path = line
                
                # Extract artist/title from filename if not set
                filename = os.path.basename(line)
                name_without_ext = os.path.splitext(filename)[0]
                
                # Remove track number prefix (e.g., "01. ", "01 - ")
                name_clean = re.sub(r'^\d+[\.\-\s]+\s*', '', name_without_ext)
                
                if not current_title:
                    if ' - ' in name_clean:
                        parts = name_clean.split(' - ', 1)
                        current_artist = current_artist or parts[0].strip()
                        current_title = parts[1].strip()
                    else:
                        current_title = name_clean
                
                tracks.append(Track(
                    filename=filename,
                    path=track_path,
                    title=current_title,
                    artist=current_artist,
                    duration=current_duration
                ))
                
                # Reset for next track
                current_title = None
                current_artist = None
                current_duration = None
    
    return Playlist(
        name=playlist_name,
        path=m3u_path,
        tracks=tracks,
        folder=folder
    )


def scan_playlists(root_path: str) -> List[Playlist]:
    """Scan directory recursively for m3u playlists"""
    playlists = []
    
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.lower().endswith('.m3u') or file.lower().endswith('.m3u8'):
                m3u_path = os.path.join(root, file)
                try:
                    playlist = parse_m3u(m3u_path)
                    if playlist.tracks:  # Only add if has tracks
                        playlists.append(playlist)
                except Exception as e:
                    print(f"Error parsing {m3u_path}: {e}")
    
    return playlists
