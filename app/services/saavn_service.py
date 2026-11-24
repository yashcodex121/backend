import base64
import html
import re
from typing import Dict, List, Optional, Any
import httpx
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives import padding

from app.config import settings
from app.models.schemas import UnifiedSong, AudioStreamQuality, LyricsResponse, AlbumResponse, PlaylistResponse


class JioSaavnService:
    def __init__(self):
        self.base_url = settings.SAAVN_BASE_URL
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.des_key = settings.SAAVN_KEY * 3

    def decrypt_url(self, enc_url: str) -> Optional[str]:
        """Decrypts JioSaavn encrypted_media_url using DES-ECB."""
        if not enc_url:
            return None
        try:
            cipher = Cipher(TripleDES(self.des_key), modes.ECB())
            decryptor = cipher.decryptor()
            encrypted_data = base64.b64decode(enc_url)
            decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
            unpadder = padding.PKCS7(64).unpadder()
            unpadded = unpadder.update(decrypted) + unpadder.finalize()
            return unpadded.decode("utf-8")
        except Exception as e:
            # Fallback or log if needed
            return None

    def get_quality_urls(self, raw_url: Optional[str]) -> List[AudioStreamQuality]:
        """Generates stream URLs for 48kbps, 96kbps, 160kbps, 320kbps."""
        if not raw_url:
            return []
        
        qualities = []
        # Standard JioSaavn media url pattern: e.g. ..._96.mp4 or .mp4
        if "_96.mp4" in raw_url:
            for kbps in ["48", "96", "160", "320"]:
                qualities.append(AudioStreamQuality(
                    quality=f"{kbps}kbps",
                    url=raw_url.replace("_96.mp4", f"_{kbps}.mp4")
                ))
        elif ".mp4" in raw_url:
            for kbps in ["48", "96", "160", "320"]:
                qualities.append(AudioStreamQuality(
                    quality=f"{kbps}kbps",
                    url=re.sub(r'(_\d+)?\.mp4$', f'_{kbps}.mp4', raw_url)
                ))
        else:
            qualities.append(AudioStreamQuality(quality="default", url=raw_url))
            
        return qualities

    def clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return html.unescape(text).strip()

    def format_thumbnails(self, img_url: Optional[str]) -> List[Dict[str, str]]:
        if not img_url:
            return []
        # Clean image URL
        img = img_url.replace("http://", "https://")
        return [
            {"quality": "low", "url": re.sub(r"\d+x\d+", "50x50", img)},
            {"quality": "medium", "url": re.sub(r"\d+x\d+", "150x150", img)},
            {"quality": "high", "url": re.sub(r"\d+x\d+", "500x500", img)},
        ]

    def format_duration(self, seconds: Optional[int]) -> str:
        if not seconds:
            return "0:00"
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    def format_song(self, raw: Dict[str, Any]) -> UnifiedSong:
        """Transforms JioSaavn song dictionary to unified model."""
        more_info = raw.get("more_info") if isinstance(raw.get("more_info"), dict) else {}
        
        song_id = str(raw.get("id") or raw.get("song_id") or "")
        title = self.clean_text(raw.get("song") or raw.get("title") or "")
        subtitle = self.clean_text(raw.get("subtitle") or "")
        
        # Extract artist names from all possible fields
        artist_names = []
        if more_info.get("artistMap") and isinstance(more_info["artistMap"], dict):
            primary = more_info["artistMap"].get("primary_artists") or []
            if isinstance(primary, list):
                artist_names = [a.get("name") for a in primary if isinstance(a, dict) and a.get("name")]
        
        artist = ""
        if artist_names:
            artist = ", ".join(artist_names)
        else:
            artist = self.clean_text(
                raw.get("primary_artists")
                or raw.get("singers")
                or raw.get("artist")
                or more_info.get("music")
                or raw.get("subtitle")
                or "Unknown Artist"
            )
        
        album = self.clean_text(raw.get("album") or more_info.get("album") or "")
        
        duration = None
        raw_dur = raw.get("duration") or more_info.get("duration")
        if raw_dur:
            try:
                duration = int(raw_dur)
            except (ValueError, TypeError):
                duration = None

        raw_image = raw.get("image") or more_info.get("image") or ""
        thumbnails = self.format_thumbnails(raw_image)
        high_thumb = thumbnails[-1]["url"] if thumbnails else raw_image.replace("http://", "https://")

        # Decrypt media URL if available (check both top-level and inside more_info)
        enc_url = raw.get("encrypted_media_url") or more_info.get("encrypted_media_url")
        decrypted_url = self.decrypt_url(enc_url) if enc_url else (raw.get("media_preview_url") or None)
        quality_options = self.get_quality_urls(decrypted_url)
        
        # Best stream URL (prefer 320kbps or 160kbps if available, else first quality)
        best_stream_url = None
        for q in quality_options:
            if q.quality == "320kbps":
                best_stream_url = q.url
                break
        if not best_stream_url and quality_options:
            best_stream_url = quality_options[-1].url

        has_lyrics = str(raw.get("has_lyrics") or more_info.get("has_lyrics", "")).lower() == "true"
        lyrics_id = str(raw.get("id", "")) if has_lyrics else None

        return UnifiedSong(
            id=song_id,
            source="jiosaavn",
            title=title,
            subtitle=subtitle,
            artist=artist,
            artists=artist,
            album=album,
            duration=duration,
            duration_str=self.format_duration(duration),
            thumbnail=high_thumb,
            image=high_thumb,
            thumbnails=thumbnails,
            stream_url=best_stream_url,
            streamUrl=best_stream_url,
            proxy_stream_url=f"/api/stream/audio?source=jiosaavn&id={song_id}",
            quality_options=quality_options,
            has_lyrics=has_lyrics,
            lyrics_id=lyrics_id,
            year=str(raw.get("year") or more_info.get("year", "")) or None,
            language=raw.get("language") or more_info.get("language") or None,
            copyright=self.clean_text(raw.get("copyright_text") or more_info.get("copyright_text") or "") or None,
            raw_data=raw,
        )

    async def search_songs(self, query: str, page: int = 1, limit: int = 20) -> List[UnifiedSong]:
        """Search songs on JioSaavn."""
        params = {
            "__call": "search.getResults",
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "web6dot0",
            "q": query,
            "p": str(page),
            "n": str(limit),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return []
            data = res.json()
            results = data.get("results", [])
            return [self.format_song(item) for item in results]

    async def get_song_details(self, song_id: str) -> Optional[UnifiedSong]:
        """Fetches complete song details by ID."""
        params = {
            "__call": "song.getDetails",
            "cc": "in",
            "_marker": "0",
            "_format": "json",
            "pids": song_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return None
            data = res.json()
            if song_id in data:
                return self.format_song(data[song_id])
            # Sometimes values are inside a list or top level
            if isinstance(data, dict) and data:
                first_key = next(iter(data))
                if isinstance(data[first_key], dict):
                    return self.format_song(data[first_key])
            return None

    async def get_album_details(self, album_id: str) -> Optional[AlbumResponse]:
        """Fetch album details with all songs."""
        params = {
            "__call": "content.getAlbumDetails",
            "_format": "json",
            "cc": "in",
            "_marker": "0",
            "albumid": album_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return None
            data = res.json()
            songs = [self.format_song(s) for s in data.get("songs", [])]
            raw_img = data.get("image", "")
            thumb = self.format_thumbnails(raw_img)
            return AlbumResponse(
                id=str(data.get("id") or album_id),
                title=self.clean_text(data.get("title") or data.get("name")),
                artist=self.clean_text(data.get("primary_artists") or ""),
                year=str(data.get("year") or ""),
                thumbnail=thumb[-1]["url"] if thumb else raw_img,
                songs_count=len(songs),
                songs=songs,
            )

    async def get_playlist_details(self, playlist_id: str) -> Optional[PlaylistResponse]:
        """Fetch playlist details with songs."""
        params = {
            "__call": "playlist.getDetails",
            "_format": "json",
            "cc": "in",
            "_marker": "0",
            "listid": playlist_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return None
            data = res.json()
            songs = [self.format_song(s) for s in data.get("songs", [])]
            raw_img = data.get("image", "")
            thumb = self.format_thumbnails(raw_img)
            return PlaylistResponse(
                id=str(data.get("id") or playlist_id),
                title=self.clean_text(data.get("title") or data.get("listname")),
                subtitle=self.clean_text(data.get("subtitle") or ""),
                thumbnail=thumb[-1]["url"] if thumb else raw_img,
                songs_count=len(songs),
                songs=songs,
            )

    async def get_lyrics(self, lyrics_id: str) -> Optional[LyricsResponse]:
        """Fetches song lyrics."""
        params = {
            "__call": "lyrics.getLyrics",
            "ctx": "web6dot0",
            "_format": "json",
            "_marker": "0",
            "lyrics_id": lyrics_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return None
            data = res.json()
            if "lyrics" in data:
                return LyricsResponse(
                    lyrics_id=lyrics_id,
                    lyrics=html.unescape(data["lyrics"]).replace("<br>", "\n"),
                    snippet=data.get("snippet"),
                    copyright_text=data.get("copyright_text"),
                )
            return None

    async def get_trending(self) -> List[UnifiedSong]:
        """Fetches trending songs from JioSaavn homepage / charts."""
        params = {
            "__call": "content.getHomepageData",
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "web6dot0",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(self.base_url, params=params, headers=self.headers)
            if res.status_code != 200:
                return []
            data = res.json()
            trending_raw = []
            if "new_trending" in data:
                trending_raw = data["new_trending"]
            elif "top_playlists" in data:
                trending_raw = data["top_playlists"]
            
            songs = []
            for item in trending_raw:
                if item.get("type") == "song":
                    songs.append(self.format_song(item))
            return songs


saavn_service = JioSaavnService()
