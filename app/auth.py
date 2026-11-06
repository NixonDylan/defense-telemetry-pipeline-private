from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_telemetry_scope(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        role: str = payload.get("role")
        if role not in ["operator", "admin", "edge_device"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for telemetry ingestion"
            )
        return payload
    except JWTError:
        raise credentials_exception
