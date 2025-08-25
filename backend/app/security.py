import hashlib
import os

SALT = os.getenv("ID_HASH_SALT", "")

def hash_sensitive(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256((SALT + value).encode()).hexdigest()