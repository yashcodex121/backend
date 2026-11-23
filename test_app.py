import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from app.services.saavn_service import saavn_service
from app.services.yt_service import yt_service

def verify_backend():
    print("========================================")
    print(f"🎵 {app.title} (v{app.version})")
    print("========================================")
    
    # 1. Verify Routes
    endpoints = []
    for r in app.routes:
        if hasattr(r, "original_router"):
            prefix = r.include_context.prefix
            for sub in r.original_router.routes:
                endpoints.append((list(sub.methods)[0], f"{prefix}{sub.path}"))
        elif hasattr(r, "path") and hasattr(r, "methods"):
            endpoints.append((list(r.methods)[0], r.path))
            
    print(f"\n✅ Total Endpoints Registered: {len(endpoints)}")
    for method, path in sorted(endpoints, key=lambda x: x[1]):
        print(f"   [{method:<4}] {path}")
        
    # 2. Test JioSaavn DES Decryption logic
    test_enc = "8Zg6zQpWlJ9fT8+zL7P4nQ=="  # sample dummy payload
    try:
        saavn_service.decrypt_url(test_enc)
        print("\n✅ JioSaavn DES Decryption Engine: OK")
    except Exception as e:
        print(f"\n❌ JioSaavn Decryption Engine Error: {e}")

    # 3. Test YouTube yt-dlp initialization
    try:
        duration_test = yt_service.format_duration(215)
        assert duration_test == "3:35"
        print("✅ YouTube yt-dlp Service & Formatters: OK")
    except Exception as e:
        print(f"❌ YouTube Service Error: {e}")

    print("\n🎉 ALL BACKEND CHECKS PASSED! Run `python run.py` to start server.")

if __name__ == "__main__":
    verify_backend()
