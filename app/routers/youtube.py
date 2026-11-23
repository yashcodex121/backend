from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Path

from app.models.schemas import SearchResponse, UnifiedSong
from app.services.yt_service import yt_service

router = APIRouter(prefix="/yt", tags=["YouTube"])


@router.get("/search", response_model=SearchResponse)
async def search_youtube(
    q: str = Query(..., description="YouTube song/video search query"),
    limit: int = Query(15, ge=1, le=50)
):
    """Fast search on YouTube/YouTube Music for songs and videos."""
    results = await yt_service.search(q, limit=limit)
    return SearchResponse(
        status="success",
        query=q,
        source="youtube",
        total=len(results),
        results=results
    )


@router.get("/song/{video_id}", response_model=UnifiedSong)
async def get_song_details(video_id: str = Path(..., description="YouTube 11-char Video ID")):
    """
    Extract complete song metadata and direct streaming audio formats for a YouTube video.
    """
    song = await yt_service.get_song_details(video_id)
    if not song:
        raise HTTPException(status_code=404, detail="YouTube video/song not found")
    return song


@router.get("/stream-url/{video_id}")
async def get_stream_url(video_id: str = Path(..., description="YouTube Video ID")):
    """Get the direct CDN audio stream URL for a YouTube video."""
    url = await yt_service.get_stream_url(video_id)
    if not url:
        raise HTTPException(status_code=404, detail="Could not extract audio stream for this YouTube ID")
    return {
        "status": "success",
        "video_id": video_id,
        "stream_url": url
    }
