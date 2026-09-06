"""Small, dependency-free text helpers shared by parsing and rendering."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WORD_SPLIT = re.compile(r"[\s\-_]+")


def slugify(value: str) -> str:
    """Return a URL- and filename-safe slug: ``"Jane Doe"`` -> ``"jane-doe"``.

    Accents are folded to ASCII so ``"José Álvarez"`` becomes ``"jose-alvarez"``.
    """
    folded = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return _NON_ALNUM.sub("-", folded).strip("-")


def initials(name: str, limit: int = 2) -> str:
    """Return up to ``limit`` initials for the monogram avatar fallback."""
    letters = [word[0].upper() for word in _WORD_SPLIT.split(name.strip()) if word]
    return "".join(letters[:limit]) or "?"


def hue_for(value: str) -> int:
    """Map a string to a stable hue (0-359).

    Uses blake2s rather than ``hash()`` because ``hash()`` is salted per
    process, which would make the generated CSS churn between builds.
    """
    digest = hashlib.blake2s(value.encode("utf-8"), digest_size=2).digest()
    return int.from_bytes(digest, "big") % 360
