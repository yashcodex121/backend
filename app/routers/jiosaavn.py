from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Path

from app.models.schemas import SearchResponse, UnifiedSong, LyricsResponse, AlbumResponse, PlaylistResponse
from app.services.saavn_service import saavn_service

router = APIRouter(prefix="/saavn", tags=["JioSaavn"])


@router.get("/search", response_model=SearchResponse)
async def search_jiosaavn(
    q: str = Query(..., description="Query for song/artist/album"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50)
):
    """Search JioSaavn songs."""
    results = await saavn_service.search_songs(q, page=page, limit=limit)
    return SearchResponse(
        status="success",
        query=q,
        source="jiosaavn",
        total=len(results),
        results=results
    )


@router.get("/song/{song_id}", response_model=UnifiedSong)
async def get_song(song_id: str = Path(..., description="JioSaavn Song ID (PID)")):
    """Get full details and decrypted streaming URLs (320k, 160k, 96k, 48k) for a song."""
    song = await saavn_service.get_song_details(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found on JioSaavn")
    return song


@router.get("/album/{album_id}", response_model=AlbumResponse)
async def get_album(album_id: str = Path(..., description="JioSaavn Album ID")):
    """Get album information with full song tracklist."""
    album = await saavn_service.get_album_details(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found on JioSaavn")
    return album


@router.get("/playlist/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: str = Path(..., description="JioSaavn Playlist ID")):
    """Get playlist information and songs."""
    playlist = await saavn_service.get_playlist_details(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found on JioSaavn")
    return playlist


@router.get("/lyrics/{lyrics_id}", response_model=LyricsResponse)
async def get_lyrics(lyrics_id: str = Path(..., description="Song / Lyrics ID")):
    """Get song lyrics."""
    lyrics = await saavn_service.get_lyrics(lyrics_id)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found for this song")
    return lyrics


@router.get("/trending", response_model=List[UnifiedSong])
async def get_trending():
    """Get currently trending songs and charts."""
    return await saavn_service.get_trending()
