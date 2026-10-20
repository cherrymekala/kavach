"""Settings for the whole suite, applied before any test module imports the app.

Two papercuts this removes:

* `PACKS_DIR` had to be exported by hand, otherwise the pack lookup fell back to
  `<repo>/packs` and a dozen tests failed with FileNotFoundError.
* `AUTH_DISABLED` was unset at import time, so tests were quietly relying on *another* file
  having cleared the settings cache first — `test_health` only passed because of ordering.
"""

import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("PACKS_DIR", str(REPO / "magellan" / "packs"))


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    """Every test starts in local mode (memory store, no Firebase) with fresh settings.

    Tests that need auth enabled set AUTH_DISABLED=false themselves, which still works because
    they clear the cache again after changing it.
    """
    monkeypatch.setenv("AUTH_DISABLED", "true")
    from kavach.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
