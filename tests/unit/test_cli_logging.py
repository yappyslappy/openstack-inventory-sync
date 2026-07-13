from __future__ import annotations

import ast
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import openstack_inventory_sync.models  # noqa: F401
from openstack_inventory_sync import cli
from openstack_inventory_sync.config import (
    AppSettings,
    InventorySettings,
    MySQLSettings,
    OpenStackSettings,
)
from openstack_inventory_sync.database.base import Base
from openstack_inventory_sync.sync.result import SyncResult

RESERVED_LOG_RECORD_KEYS = {
    *logging.makeLogRecord({}).__dict__.keys(),
    "asctime",
    "message",
    "taskName",
}


def app_settings(lock_dir: str) -> AppSettings:
    return AppSettings(
        inventory=InventorySettings(
            scope_key="appdev",
            openstack_project_id="project-appdev",
            openstack_project_name="DF-APPDEV",
            lock_dir=lock_dir,
        ),
        openstack=OpenStackSettings(
            auth_url="https://identity.example/v3",
            application_credential_id="credential-id",
            application_credential_secret="secret",
            region_name="RegionOne",
            interface="internal",
        ),
        mysql=MySQLSettings(
            host="db.example",
            port=3306,
            database="inventory",
            username="sync_user",
            password="db-secret",
        ),
        log_level="INFO",
    )


def test_ensure_source_context_info_log_uses_safe_extra_keys(
    sqlite_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    caplog.set_level(logging.INFO, logger=cli.logger.name)

    source = cli.ensure_source_context(app_settings(str(tmp_path)), sqlite_session_factory)

    record = next(
        record for record in caplog.records if record.getMessage() == "inventory_source.ready"
    )
    structured_record = cast(Any, record)
    assert source.scope_key == "appdev"
    assert structured_record.inventory_scope == "appdev"
    assert structured_record.openstack_project_id == "project-appdev"
    assert structured_record.openstack_project_name == "DF-APPDEV"
    assert structured_record.inventory_source_created is True
    assert isinstance(record.created, float)
    assert record.created != structured_record.inventory_source_created


def test_structured_logging_extra_literals_do_not_use_reserved_log_record_keys() -> None:
    collisions: list[str] = []
    for path in sorted((Path(__file__).resolve().parents[2] / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg == "extra" and isinstance(keyword.value, ast.Dict):
                    for key in keyword.value.keys:
                        if (
                            isinstance(key, ast.Constant)
                            and isinstance(key.value, str)
                            and key.value in RESERVED_LOG_RECORD_KEYS
                        ):
                            collisions.append(f"{path}:{node.lineno}:{key.value}")

    assert not collisions


def test_sync_result_log_payload_does_not_use_reserved_log_record_keys() -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    payload = SyncResult(
        resource="servers",
        inventory_scope="appdev",
        openstack_project_id="project-appdev",
        openstack_project_name="DF-APPDEV",
        started_at=now,
        completed_at=now,
        fetched=1,
        inserted=1,
        updated=0,
        unchanged=0,
        deleted=0,
        removed=0,
        rejected=0,
    ).as_log_dict()

    assert not (set(payload) & RESERVED_LOG_RECORD_KEYS)


class FakeAuth:
    def get_project_id(self, session: object) -> str:
        return "project-appdev"


class FakeSession:
    auth = FakeAuth()


class FakeConnection:
    session = FakeSession()


class FakeClient:
    def list_servers(self) -> list[dict[str, object]]:
        return [
            {
                "id": "server-1",
                "name": "web-01",
                "project_id": "project-appdev",
                "status": "ACTIVE",
                "image": {"id": "image-1"},
                "flavor": {"id": "flavor-1"},
            }
        ]


def test_cli_sync_servers_reaches_synchronizer_with_info_logging(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    reached = False
    settings = app_settings(str(tmp_path))

    class TrackingClient(FakeClient):
        def list_servers(self) -> list[dict[str, object]]:
            nonlocal reached
            reached = True
            return super().list_servers()

    monkeypatch.setattr(
        "openstack_inventory_sync.cli.AppSettings.from_env",
        lambda env_file=None: settings,
    )
    monkeypatch.setattr(cli, "create_mysql_engine", lambda mysql_settings: engine)
    monkeypatch.setattr(
        cli, "create_openstack_connection", lambda openstack_settings: FakeConnection()
    )
    monkeypatch.setattr(cli, "OpenStackInventoryClient", lambda connection: TrackingClient())

    try:
        assert cli.main(["sync", "servers"]) == 0
        assert reached is True
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_unexpected_exception_logs_traceback_and_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger=cli.logger.name)
    monkeypatch.setattr(cli, "configure_logging", lambda level="INFO": None)

    def raise_unexpected(env_file: str | None = None) -> AppSettings:
        raise RuntimeError("boom")

    monkeypatch.setattr("openstack_inventory_sync.cli.AppSettings.from_env", raise_unexpected)

    assert cli.main(["sync", "servers"]) == 1
    record = next(record for record in caplog.records if record.getMessage() == "unexpected_error")
    structured_record = cast(Any, record)
    assert record.exc_info is not None
    assert structured_record.application_error == "Unhandled failure"
