"""
Auth middleware — API Key authentication
"""
import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JARVIS_API_KEY = os.getenv("JARVIS_API_KEY", "change-me-in-env")
security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    if credentials.credentials != JARVIS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
