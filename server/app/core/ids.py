"""Prefixed ULID identifiers, e.g. ``dev_01JXYZ...``.

Immutable, sortable-by-time IDs used for all public entity identifiers
(§10 device_id, §62 msg_ ids, ...).
"""

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode(value: int, length: int) -> str:
    out = ""
    for _ in range(length):
        out = _CROCKFORD[value & 0x1F] + out
        value >>= 5
    return out


def ulid() -> str:
    """26-char Crockford-base32 ULID: 48-bit ms timestamp + 80-bit randomness."""
    ts = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    return _encode(ts, 10) + _encode(rand, 16)


def new_id(prefix: str) -> str:
    return f"{prefix}_{ulid()}"
