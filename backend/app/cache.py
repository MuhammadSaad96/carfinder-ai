import time
import hashlib
import logging

logger = logging.getLogger(__name__)

_store: dict = {}
TTL = 1800  # 30 minutes


def _key(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def get(query: str):
    k = _key(query)
    entry = _store.get(k)
    if entry and time.time() - entry["ts"] < TTL:
        logger.info(f"Cache HIT for: {query!r}")
        return entry["data"]
    if entry:
        del _store[k]
    return None


def set(query: str, data):
    k = _key(query)
    _store[k] = {"ts": time.time(), "data": data}
    logger.info(f"Cache SET for: {query!r} ({len(_store)} entries total)")


def clear_expired():
    now = time.time()
    expired = [k for k, v in _store.items() if now - v["ts"] >= TTL]
    for k in expired:
        del _store[k]
    return len(expired)
