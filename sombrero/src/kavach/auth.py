from fastapi import Depends, Header, HTTPException

from .config import Settings, get_settings


def verify_token(token: str | None, settings: Settings) -> str:
    """Firebase ID token -> uid. Used by HTTP routes and the hearing WebSocket."""
    if settings.auth_disabled:
        return "dev-user"
    if not token:
        raise HTTPException(401, "Sign in again: the login token is missing.")
    from firebase_admin import auth, get_app, initialize_app

    try:
        get_app()
    except ValueError:
        initialize_app()
    try:
        return auth.verify_id_token(token)["uid"]
    except Exception as exc:
        raise HTTPException(401, "Sign in again: the login token has expired.") from exc


def current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Return the Firebase uid for the request."""
    token = (
        authorization.removeprefix("Bearer ")
        if authorization and authorization.startswith("Bearer ")
        else None
    )
    return verify_token(token, settings)
