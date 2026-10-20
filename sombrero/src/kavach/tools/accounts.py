"""Find a Kavach account from the phone number that reached us.

Both non-web channels (the Twilio phone line and WhatsApp) identify the caller by the number
they contact us from. Because sign-in is Firebase phone OTP, that number already maps to a uid
and therefore to the patient's cases — no separate linking step, and no passwords.
"""

from ..config import get_settings


def to_e164(raw: str) -> str:
    """WhatsApp sends digits only ("919493925966"); Firebase stores "+919493925966"."""
    digits = "".join(ch for ch in raw or "" if ch.isdigit())
    return f"+{digits}" if digits else ""


def uid_for_phone(raw: str) -> str | None:
    """The uid that signed in with this number, or None if nobody has."""
    s = get_settings()
    if s.auth_disabled:
        return "dev-user"
    phone = to_e164(raw)
    if not phone:
        return None
    from firebase_admin import auth, get_app, initialize_app

    try:
        get_app()
    except ValueError:
        initialize_app()
    try:
        return auth.get_user_by_phone_number(phone).uid
    except (auth.UserNotFoundError, ValueError):  # ValueError: malformed number
        return None
