"""Entry point so the app can be launched with ``python -m app``.

Respects the HOST/PORT environment variables (see app.config).
"""

import uvicorn

from .config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
