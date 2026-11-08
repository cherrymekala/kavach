"""Devices that want tracker reminders as web push notifications."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import current_user
from ..tools import store

router = APIRouter(prefix="/push", tags=["push"])


class PushToken(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


@router.post("/tokens", status_code=204)
def add_token(body: PushToken, uid: str = Depends(current_user)) -> None:
    """Turn reminders on for this browser (the FCM registration token)."""
    store.save_push_token(uid, body.token)


@router.post("/tokens/remove", status_code=204)
def remove_token(body: PushToken, uid: str = Depends(current_user)) -> None:
    """Turn reminders off for this browser. Tokens are long, so they go in the body, not the URL."""
    store.delete_push_token(body.token, uid)
