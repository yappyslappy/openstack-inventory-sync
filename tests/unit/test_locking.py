from __future__ import annotations

from pathlib import Path

import pytest

from openstack_inventory_sync.exceptions import SourceLockError
from openstack_inventory_sync.sync.locking import sanitize_scope_for_path, source_lock


def test_source_specific_lock_blocks_same_scope(tmp_path: Path) -> None:
    with (
        source_lock("appdev", str(tmp_path)),
        pytest.raises(SourceLockError, match="already running"),
        source_lock("appdev", str(tmp_path)),
    ):
        pass


def test_different_scopes_can_lock_concurrently(tmp_path: Path) -> None:
    with (
        source_lock("appdev", str(tmp_path)) as appdev_lock,
        source_lock("apptest", str(tmp_path)) as apptest_lock,
    ):
        assert appdev_lock != apptest_lock


def test_scope_lock_name_is_sanitized() -> None:
    assert sanitize_scope_for_path("app/dev") == "app-dev"
