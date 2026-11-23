import asyncio
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.models.schemas import SearchResponse, UnifiedSong
from app.services.saavn_service import saavn_service
from app.services.yt_service import yt_service

router = APIRouter(prefix="/unified", tags=["Unified Music"])


@router.get("/search", response_model=SearchResponse)
async def unified_search(
    q: str = Query(..., description="Song / Artist / Album search query"),
    limit: int = Query(10, ge=1, le=50, description="Results limit per source"),
    source: str = Query("all", description="Source: 'all', 'jiosaavn', or 'youtube'")
):
    """
    Search across JioSaavn and YouTube simultaneously.
    Returns merged standardized music results.
    """
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    results = []

    if source.lower() == "jiosaavn":
        results = await saavn_service.search_songs(query, limit=limit)
    elif source.lower() == "youtube":
        results = await yt_service.search(query, limit=limit)
    else:
        # Search both concurrently with asyncio.gather
        saavn_task = saavn_service.search_songs(query, limit=limit)
        yt_task = yt_service.search(query, limit=limit)
        
        saavn_res, yt_res = await asyncio.gather(saavn_task, yt_task, return_exceptions=True)
        
        saavn_list = saavn_res if isinstance(saavn_res, list) else []
        yt_list = yt_res if isinstance(yt_res, list) else []

        # Interleave results for a balanced feed (JioSaavn has direct 320kbps MP4s, YT has live versions & official tracks)
        max_len = max(len(saavn_list), len(yt_list))
        for i in range(max_len):
            if i < len(saavn_list):
                results.append(saavn_list[i])
            if i < len(yt_list):
                results.append(yt_list[i])

    return SearchResponse(
        status="success",
        query=query,
        source=source,
        total=len(results),
        results=results,
    )


@router.get("/song", response_model=UnifiedSong)
async def get_song(
    source: str = Query(..., description="'jiosaavn' or 'youtube'"),
    id: str = Query(..., description="Song ID or YouTube Video ID")
):
    """
    Get detailed song information and direct streaming links from either source.
    """
    src = source.lower()
    if src == "jiosaavn":
        song = await saavn_service.get_song_details(id)
        if not song:
            raise HTTPException(status_code=404, detail="JioSaavn song not found")
        return song
    elif src == "youtube":
        song = await yt_service.get_song_details(id)
        if not song:
            raise HTTPException(status_code=404, detail="YouTube song / video not found")
        return song
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Use 'jiosaavn' or 'youtube'")
