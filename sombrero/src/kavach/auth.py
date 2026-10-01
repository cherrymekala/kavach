from fastapi import Depends, Header, HTTPException

from .config import Settings, get_settings


def current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Return the Firebase uid for the request."""
    if settings.auth_disabled:
        return "dev-user"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in again: the login token is missing.")
    from firebase_admin import auth, get_app, initialize_app

    try:
        get_app()
    except ValueError:
        initialize_app()
    try:
        return auth.verify_id_token(authorization.removeprefix("Bearer "))["uid"]
    except Exception as exc:
        raise HTTPException(401, "Sign in again: the login token has expired.") from exc
