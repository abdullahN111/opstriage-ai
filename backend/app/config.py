import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
    )

    GOOGLE_DRIVE_SOP_FOLDER_ID: str = os.getenv(
        "GOOGLE_DRIVE_SOP_FOLDER_ID", "1MJ11K1jCYC_RkQ6DejdrkAmxUXTb_qVU"
    )
    GOOGLE_SHEETS_TRACKER_ID: str = os.getenv(
        "GOOGLE_SHEETS_TRACKER_ID", "1mEVTzPE9fQxoQP78hJsiSPq6uucLyy_m_1cOJkJwqek"
    )

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "ak8757796@gmail.com")
    ADMIN_PASSKEY: str = os.getenv("ADMIN_PASSKEY", "admin123")
    TOKEN_PATH: Path = BASE_DIR / "token.json"

    GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]


settings = Settings()
