import os

class Settings:
    PROJECT_NAME: str = "MusicFlow API (YouTube + JioSaavn)"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # JioSaavn Configuration
    SAAVN_BASE_URL: str = "https://www.jiosaavn.com/api.php"
    SAAVN_KEY: bytes = b"38346591"
    
    # User-Agent for requests
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

settings = Settings()
