from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class AudioStreamQuality(BaseModel):
    quality: str  # e.g. "320kbps", "160kbps", "96kbps", "48kbps", "auto"
    url: str

class UnifiedSong(BaseModel):
    id: str
    source: str = Field(..., description="'jiosaavn' or 'youtube'")
    title: str
    subtitle: Optional[str] = None
    artist: str
    artists: Optional[str] = None  # Frontend compatibility
    album: Optional[str] = None
    duration: Optional[int] = Field(None, description="Duration in seconds")
    duration_str: Optional[str] = None
    thumbnail: Optional[str] = None
    image: Optional[str] = None  # Frontend compatibility
    thumbnails: Optional[List[Dict[str, str]]] = None
    stream_url: Optional[str] = Field(None, description="Direct audio CDN/streaming URL")
    streamUrl: Optional[str] = None  # Frontend compatibility
    proxy_stream_url: Optional[str] = Field(None, description="Local backend proxy URL for direct player playback")
    youtubeUrl: Optional[str] = None  # Frontend compatibility
    quality_options: Optional[List[AudioStreamQuality]] = None
    has_lyrics: Optional[bool] = False
    lyrics_id: Optional[str] = None
    year: Optional[str] = None
    language: Optional[str] = None
    copyright: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    status: str = "success"
    success: bool = True  # Frontend compatibility
    query: str
    source: str  # "unified", "jiosaavn", "youtube"
    total: int
    results: List[UnifiedSong]

class LyricsResponse(BaseModel):
    status: str = "success"
    lyrics_id: Optional[str] = None
    lyrics: str
    snippet: Optional[str] = None
    copyright_text: Optional[str] = None

class AlbumResponse(BaseModel):
    id: str
    title: str
    artist: Optional[str] = None
    year: Optional[str] = None
    thumbnail: Optional[str] = None
    songs_count: int = 0
    songs: List[UnifiedSong] = []

class PlaylistResponse(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    thumbnail: Optional[str] = None
    songs_count: int = 0
    songs: List[UnifiedSong] = []
