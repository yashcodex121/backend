from typing import Optional
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
import httpx

from app.services.saavn_service import saavn_service
from app.services.yt_service import yt_service

router = APIRouter(prefix="/stream", tags=["Streaming"])


@router.get("/audio")
async def stream_audio(
    request: Request,
    source: str = Query(..., description="'jiosaavn' or 'youtube'"),
    id: str = Query(..., description="Song ID or Video ID"),
    bitrate: Optional[str] = Query("320", description="Preferred bitrate for JioSaavn: 320, 160, 96, 48"),
    redirect: bool = Query(False, description="Redirect directly to CDN instead of proxy streaming")
):
    """
    Streams audio directly or proxies chunked audio data with HTTP Range support.
    Ideal for HTML5 audio tags:
    `<audio controls src="/api/stream/audio?source=jiosaavn&id=ABC"></audio>`
    """
    src = source.lower()
    target_url = None

    if src == "jiosaavn":
        song = await saavn_service.get_song_details(id)
        if not song or not song.quality_options:
            raise HTTPException(status_code=404, detail="Song stream not found on JioSaavn")
        
        # Match preferred bitrate
        for q in song.quality_options:
            if f"{bitrate}kbps" in q.quality:
                target_url = q.url
                break
        if not target_url:
            target_url = song.stream_url or (song.quality_options[0].url if song.quality_options else None)

    elif src == "youtube":
        target_url = await yt_service.get_stream_url(id)
        if not target_url:
            raise HTTPException(status_code=404, detail="Audio stream not found on YouTube")
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Choose 'jiosaavn' or 'youtube'")

    if not target_url:
        raise HTTPException(status_code=404, detail="Audio URL could not be resolved")

    # If client requested 302 redirect directly to CDN
    if redirect:
        return RedirectResponse(url=target_url, status_code=307)

    # Proxy streaming with Range header forwarding for seekable playback
    client_range = request.headers.get("range")
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if client_range:
        req_headers["range"] = client_range

    async def audio_stream_generator():
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", target_url, headers=req_headers) as response:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    yield chunk

    # Inspect headers
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            head_res = await client.head(target_url, headers=req_headers)
            content_type = head_res.headers.get("content-type", "audio/mp4")
            content_length = head_res.headers.get("content-length")
            content_range = head_res.headers.get("content-range")
            status_code = 206 if client_range else 200

            resp_headers = {
                "Accept-Ranges": "bytes",
                "Content-Type": content_type,
            }
            if content_length:
                resp_headers["Content-Length"] = content_length
            if content_range:
                resp_headers["Content-Range"] = content_range

            return StreamingResponse(
                audio_stream_generator(),
                status_code=status_code,
                headers=resp_headers
            )
    except Exception:
        # Fallback to simple stream
        return StreamingResponse(
            audio_stream_generator(),
            media_type="audio/mp4"
        )
