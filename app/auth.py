from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

ALLOWED_TELEMETRY_ROLES = {"operator", "admin", "edge_device"}


async def verify_telemetry_scope(
    token: str = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Decode and validate a bearer JWT and confirm an allowed telemetry role."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise credentials_exception from exc

    role = payload.get("role")
    if not isinstance(role, str) or role not in ALLOWED_TELEMETRY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for telemetry ingestion",
        )

    return payload
