import os
import sys
import argparse
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicFlow YouTube + JioSaavn Backend")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host IP to bind")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port number")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    
    args = parser.parse_args()

    print(f"🎵 Starting MusicFlow Backend on http://localhost:{args.port}")
    print(f"📖 Swagger Docs available at http://localhost:{args.port}/docs")
    print(f"⚡ Press CTRL+C to stop the server\n")

    if args.reload:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")]
        )
    else:
        from app.main import app
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info"
        )
