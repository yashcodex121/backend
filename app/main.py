from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import unified, jiosaavn, youtube, stream
from app.models import schemas

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Unified High-Performance Streaming & Search Backend for YouTube & JioSaavn",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for all frontends (React, Next.js, React Native, Flutter, Vue)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(unified.router, prefix=settings.API_PREFIX)
app.include_router(jiosaavn.router, prefix=settings.API_PREFIX)
app.include_router(youtube.router, prefix=settings.API_PREFIX)
app.include_router(stream.router, prefix=settings.API_PREFIX)

# Compatibility direct aliases for frontends using /api/jiosaavn or /api/youtube
@app.get("/api/jiosaavn/search", response_model=schemas.SearchResponse, tags=["Compatibility"])
async def alias_jiosaavn_search(
    q: str = Query(..., description="Query for song/artist/album"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50)
):
    return await jiosaavn.search_jiosaavn(q=q, page=page, limit=limit)

@app.get("/api/youtube/search", response_model=schemas.SearchResponse, tags=["Compatibility"])
async def alias_youtube_search(
    q: str = Query(..., description="YouTube song/video search query"),
    limit: int = Query(15, ge=1, le=50)
):
    return await youtube.search_youtube(q=q, limit=limit)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "unified_search": f"{settings.API_PREFIX}/unified/search?q={{query}}&limit={{limit}}&source={{all|jiosaavn|youtube}}",
            "unified_song": f"{settings.API_PREFIX}/unified/song?source={{jiosaavn|youtube}}&id={{id}}",
            "jiosaavn_search": f"{settings.API_PREFIX}/saavn/search?q={{query}}",
            "jiosaavn_song": f"{settings.API_PREFIX}/saavn/song/{{song_id}}",
            "jiosaavn_album": f"{settings.API_PREFIX}/saavn/album/{{album_id}}",
            "jiosaavn_playlist": f"{settings.API_PREFIX}/saavn/playlist/{{playlist_id}}",
            "jiosaavn_lyrics": f"{settings.API_PREFIX}/saavn/lyrics/{{lyrics_id}}",
            "jiosaavn_trending": f"{settings.API_PREFIX}/saavn/trending",
            "youtube_search": f"{settings.API_PREFIX}/yt/search?q={{query}}",
            "youtube_song": f"{settings.API_PREFIX}/yt/song/{{video_id}}",
            "youtube_stream_url": f"{settings.API_PREFIX}/yt/stream-url/{{video_id}}",
            "audio_stream_proxy": f"{settings.API_PREFIX}/stream/audio?source={{jiosaavn|youtube}}&id={{id}}&bitrate={{320|160|96|48}}"
        }
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}
