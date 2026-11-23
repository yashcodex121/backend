import asyncio
import re
from typing import Dict, List, Optional, Any
import yt_dlp

from app.models.schemas import UnifiedSong, AudioStreamQuality


class YouTubeService:
    def __init__(self):
        self.default_ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
            "noplaylist": True,
        }

    def format_duration(self, seconds: Optional[int]) -> str:
        if not seconds:
            return "0:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def format_thumbnails(self, video_id: str, raw_thumbnails: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
        if raw_thumbnails and len(raw_thumbnails) > 0:
            return [
                {"quality": "default", "url": t.get("url", "")}
                for t in raw_thumbnails if t.get("url")
            ]
        # Fallback standard YouTube thumbnails
        return [
            {"quality": "low", "url": f"https://i.ytimg.com/vi/{video_id}/default.jpg"},
            {"quality": "medium", "url": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"},
            {"quality": "high", "url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"},
            {"quality": "max", "url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"},
        ]

    def _sync_search(self, query: str, limit: int = 15) -> List[UnifiedSong]:
        """Performs flat search on YouTube (fast, does not resolve stream URLs)."""
        search_query = f"ytsearch{limit}:{query}"
        opts = {
            **self.default_ydl_opts,
            "extract_flat": True,
        }
        
        songs = []
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                entries = info.get("entries", []) if info else []
                for entry in entries:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    if not video_id:
                        continue
                        
                    duration = entry.get("duration")
                    title = entry.get("title", "")
                    uploader = entry.get("uploader") or entry.get("channel") or "YouTube Music"
                    
                    # Generate thumbs
                    thumbnails = self.format_thumbnails(video_id, entry.get("thumbnails"))
                    high_thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    
                    song = UnifiedSong(
                        id=video_id,
                        source="youtube",
                        title=title,
                        subtitle=uploader,
                        artist=uploader,
                        artists=uploader,
                        album="YouTube Single",
                        duration=int(duration) if duration else None,
                        duration_str=self.format_duration(duration),
                        thumbnail=high_thumb,
                        image=high_thumb,
                        thumbnails=thumbnails,
                        stream_url=None,  # Resolved on demand or played via proxy
                        streamUrl=f"https://www.youtube.com/watch?v={video_id}",
                        youtubeUrl=f"https://www.youtube.com/watch?v={video_id}",
                        proxy_stream_url=f"/api/stream/audio?source=youtube&id={video_id}",
                        quality_options=[],
                        has_lyrics=False,
                        raw_data={
                            "url": entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                            "view_count": entry.get("view_count"),
                        }
                    )
                    songs.append(song)
            except Exception as e:
                # Log error if needed
                pass

        return songs

    def _sync_get_info(self, video_id: str) -> Optional[UnifiedSong]:
        """Resolves detailed video info including all available audio streams and best direct stream URL."""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {
            **self.default_ydl_opts,
            "format": "bestaudio/best",
        }
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                if not info:
                    return None
                
                formats = info.get("formats", [])
                audio_qualities = []
                best_audio_url = None
                
                # Filter formats with audio
                for f in formats:
                    acodec = f.get("acodec")
                    url = f.get("url")
                    abr = f.get("abr") or f.get("tbr")
                    ext = f.get("ext")
                    
                    if acodec and acodec != "none" and url:
                        bitrate_label = f"{int(abr)}kbps ({ext})" if abr else f"Audio ({ext})"
                        audio_qualities.append(AudioStreamQuality(
                            quality=bitrate_label,
                            url=url
                        ))
                
                # Check for direct URL selected by yt-dlp
                if info.get("url"):
                    best_audio_url = info.get("url")
                elif audio_qualities:
                    best_audio_url = audio_qualities[-1].url
                
                duration = info.get("duration")
                title = info.get("title", "")
                uploader = info.get("uploader") or info.get("channel") or "Unknown"
                thumbnails = self.format_thumbnails(video_id, info.get("thumbnails"))
                high_thumb = info.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                
                return UnifiedSong(
                    id=video_id,
                    source="youtube",
                    title=title,
                    subtitle=uploader,
                    artist=uploader,
                    album=info.get("album") or "YouTube",
                    duration=int(duration) if duration else None,
                    duration_str=self.format_duration(duration),
                    thumbnail=high_thumb,
                    thumbnails=thumbnails,
                    stream_url=best_audio_url,
                    proxy_stream_url=f"/api/stream/audio?source=youtube&id={video_id}",
                    quality_options=audio_qualities,
                    has_lyrics=False,
                    year=str(info.get("upload_date", ""))[:4] or None,
                    raw_data={
                        "webpage_url": info.get("webpage_url"),
                        "view_count": info.get("view_count"),
                        "description": info.get("description"),
                    }
                )
            except Exception as e:
                return None

    def _sync_get_stream_url(self, video_id: str) -> Optional[str]:
        """Quickly resolves only the direct audio stream URL."""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {
            **self.default_ydl_opts,
            "format": "bestaudio/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                return info.get("url") if info else None
            except Exception:
                return None

    async def search(self, query: str, limit: int = 15) -> List[UnifiedSong]:
        return await asyncio.to_thread(self._sync_search, query, limit)

    async def get_song_details(self, video_id: str) -> Optional[UnifiedSong]:
        return await asyncio.to_thread(self._sync_get_info, video_id)

    async def get_stream_url(self, video_id: str) -> Optional[str]:
        return await asyncio.to_thread(self._sync_get_stream_url, video_id)


yt_service = YouTubeService()
