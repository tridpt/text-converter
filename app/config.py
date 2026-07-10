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
        # Use Pandoc for high-fidelity conversions when available.
        # Set USE_PANDOC=0 to force the pure-Python converters.
        self.use_pandoc: bool = os.getenv("USE_PANDOC", "1") not in (
            "0",
            "false",
            "False",
        )
        # Optional API key. If set, conversion endpoints require the
        # `X-API-Key` header. Empty means the API is open.
        self.api_key: str = os.getenv("API_KEY", "").strip()
        # Per-IP request cap for conversion endpoints, per minute. 0 disables.
        self.rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "0"))
        # Strip scripts / active content from HTML output (recommended on).
        self.sanitize_html: bool = os.getenv("SANITIZE_HTML", "1") not in (
            "0",
            "false",
            "False",
        )
        # Logging.
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_json: bool = os.getenv("LOG_JSON", "0") not in ("0", "false", "False")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
