"""Source-specific synchronization locking."""

from __future__ import annotations

import fcntl
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from openstack_inventory_sync.exceptions import SourceLockError

LOCK_SCOPE_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def sanitize_scope_for_path(scope_key: str) -> str:
    sanitized = LOCK_SCOPE_PATTERN.sub("-", scope_key).strip(".-")
    if not sanitized:
        raise SourceLockError("INVENTORY_SCOPE cannot be converted to a safe lock name")
    return sanitized


@contextmanager
def source_lock(scope_key: str, lock_dir: str) -> Iterator[Path]:
    directory = Path(lock_dir)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / f"openstack-inventory-sync-{sanitize_scope_for_path(scope_key)}.lock"

    with lock_path.open("a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SourceLockError(
                f"Sync is already running for inventory scope: {scope_key}"
            ) from exc
        try:
            yield lock_path
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
