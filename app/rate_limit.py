from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt

from app.config import settings


def rate_limit_key(request):
    """Use user_id when authenticated, otherwise fall back to client IP."""
    authorization_header = request.headers.get("authorization")
    if authorization_header and authorization_header.lower().startswith("bearer "):
        token = authorization_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("user_id")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            # Token inválido: cair para IP para evitar bypass do limitador
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=[],  # Limites apenas onde explicitamente aplicado
)
