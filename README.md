# 🎵 MusicFlow - Unified YouTube & JioSaavn Backend

High-performance, async music backend written in Python (FastAPI). It integrates **YouTube** (via `yt-dlp`) and **JioSaavn** (via native DES media decryption & direct CDN access) with a unified search interface and audio streaming proxy.

---

## 🌟 Features

- **Unified Multi-Source Search**: Search across both JioSaavn and YouTube concurrently in a single API call (`/api/unified/search?q=...`).
- **JioSaavn Full Integration**:
  - Direct 320kbps, 160kbps, 96kbps, 48kbps MP4/M4A media decryption.
  - Song details, Album tracks, Playlist tracks, Trending charts, and Song Lyrics.
- **YouTube Full Integration**:
  - Fast search with flat extraction (low latency).
  - Complete audio stream format extractor (m4a, webm, opus) with bitrates.
- **Seamless Audio Streaming Proxy**:
  - Endpoint `/api/stream/audio?source=...&id=...` handles **HTTP Range requests (`bytes=0-`)** for scrub/seek support in HTML5 `<audio>` tags.
  - Bypasses CDN CORS / 403 Forbidden issues on browsers and mobile webviews.
- **Production-Ready**:
  - Interactive Swagger UI docs at `/docs`.
  - ReDoc at `/redoc`.
  - Cross-Origin Resource Sharing (CORS) enabled for all frontends (React, Next.js, Flutter, Vue, React Native).

---

## 📁 Project Structure

```
music-backend/
├── app/
│   ├── models/
│   │   └── schemas.py          # Unified Song, Search, Album & Playlist Pydantic models
│   ├── routers/
│   │   ├── unified.py          # Combined multi-source search & detail router
│   │   ├── jiosaavn.py         # JioSaavn songs, albums, playlists, lyrics, trending
│   │   ├── youtube.py          # YouTube search, video audio extraction, direct stream
│   │   └── stream.py           # Range-supporting audio streaming proxy
│   ├── services/
│   │   ├── saavn_service.py    # JioSaavn API client & DES cipher decryption
│   │   └── yt_service.py       # Async yt-dlp audio extraction engine
│   ├── config.py               # Settings & configuration
│   ├── main.py                 # FastAPI application & router mounts
│   └── __init__.py
├── run.py                      # Server entry point
├── test_app.py                 # Health and route test script
├── requirements.txt            # Python dependencies
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### 1. Run Server
From the project folder:
```bash
python run.py
```
Default server starts on: **`http://localhost:8000`**  
Interactive API Docs (Swagger UI): **`http://localhost:8000/docs`**

---

## 📡 API Endpoints

### 1. Unified Endpoints
| Method | Endpoint | Query / Path Params | Description |
|---|---|---|---|
| `GET` | `/api/unified/search` | `q` (string), `limit` (int), `source` (`all` \| `jiosaavn` \| `youtube`) | Concurrently search both platforms |
| `GET` | `/api/unified/song` | `source` (`jiosaavn` \| `youtube`), `id` (string) | Unified song metadata & audio streams |

### 2. JioSaavn Endpoints
| Method | Endpoint | Query / Path Params | Description |
|---|---|---|---|
| `GET` | `/api/saavn/search` | `q` (string), `page` (int), `limit` (int) | Search JioSaavn tracks |
| `GET` | `/api/saavn/song/{song_id}` | `song_id` (PID string) | Decrypted 320k/160k/96k/48k audio streams |
| `GET` | `/api/saavn/album/{album_id}` | `album_id` | Get album metadata and all track details |
| `GET` | `/api/saavn/playlist/{playlist_id}` | `playlist_id` | Get playlist details and songs |
| `GET` | `/api/saavn/lyrics/{lyrics_id}` | `lyrics_id` | Song lyrics |
| `GET` | `/api/saavn/trending` | - | Currently trending songs |

### 3. YouTube Endpoints
| Method | Endpoint | Query / Path Params | Description |
|---|---|---|---|
| `GET` | `/api/yt/search` | `q` (string), `limit` (int) | Fast YouTube search |
| `GET` | `/api/yt/song/{video_id}` | `video_id` (11-char ID) | Full YouTube track metadata & audio streams |
| `GET` | `/api/yt/stream-url/{video_id}` | `video_id` | Direct audio CDN stream URL |

### 4. Audio Streaming Proxy
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stream/audio?source={jiosaavn\|youtube}&id={id}&bitrate=320` | Proxies audio stream with Range header support (`bytes=...`) for HTML5 audio tags |

---

## 💻 Frontend Usage Example (JavaScript / React)

### 1. Search Music
```javascript
const response = await fetch("http://localhost:8000/api/unified/search?q=Kesariya&limit=10");
const data = await response.json();
console.log(data.results);
```

### 2. Play Audio in HTML5 `<audio>`
```html
<!-- Direct streaming using backend proxy -->
<audio controls src="http://localhost:8000/api/stream/audio?source=jiosaavn&id=4nlv9S9r"></audio>
<audio controls src="http://localhost:8000/api/stream/audio?source=youtube&id=BddP6PYo2gs"></audio>
```
