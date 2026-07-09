"""Application configuration, sourced from environment variables."""

from __future__ import annotations

import os


class Settings:
    """Runtime settings read from the environment (with sensible defaults)."""

    def __init__(self) -> None:
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "8000"))
        # Maximum accepted upload size for a single request, in megabytes.
        self.max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
