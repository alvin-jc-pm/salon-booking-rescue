import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import admin_api_key

# Read once at start-up, so a missing key stops the app from starting at all.
ADMIN_API_KEY = admin_api_key()

# A header, not the URL: URLs end up in access logs, browser history and proxies.
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin(key: str | None = Security(admin_key_header)):
    # compare_digest takes the same time however much of the key matches.
    if key is None or not hmac.compare_digest(key.encode(), ADMIN_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Missing or wrong X-Admin-Key header")
