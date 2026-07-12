from __future__ import annotations

from typing import Any

import pytest

from openstack_inventory_sync.config import OpenStackSettings
from openstack_inventory_sync.exceptions import OpenStackConnectionError, ProjectScopeMismatchError
from openstack_inventory_sync.openstack import connection as connection_module
from openstack_inventory_sync.openstack.validation import validate_authenticated_project


def settings() -> OpenStackSettings:
    return OpenStackSettings(
        auth_url="https://identity.example/v3",
        application_credential_id="credential-id",
        application_credential_secret="secret-value",
        region_name="RegionOne",
        interface="internal",
    )


def test_create_openstack_connection_uses_application_credentials_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    expected_connection = object()

    def fake_connect(**kwargs: Any) -> object:
        captured.update(kwargs)
        return expected_connection

    monkeypatch.setattr(
        "openstack_inventory_sync.openstack.connection.openstack.connect", fake_connect
    )

    result = connection_module.create_openstack_connection(settings())

    assert result is expected_connection
    assert captured["auth_type"] == "v3applicationcredential"
    assert captured["application_credential_id"] == "credential-id"
    assert captured["application_credential_secret"] == "secret-value"
    assert "project_id" not in captured
    assert "project_name" not in captured
    assert "username" not in captured
    assert "password" not in captured


def test_create_openstack_connection_redacts_failure_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_connect(**kwargs: Any) -> object:
        raise RuntimeError("secret-value token exploded")

    monkeypatch.setattr(
        "openstack_inventory_sync.openstack.connection.openstack.connect", fake_connect
    )

    with pytest.raises(OpenStackConnectionError) as exc_info:
        connection_module.create_openstack_connection(settings())

    assert "secret-value" not in str(exc_info.value)
    assert "token" not in str(exc_info.value)


class FakeAuth:
    def __init__(self, project_id: str | None) -> None:
        self.project_id = project_id

    def get_project_id(self, session: object) -> str | None:
        return self.project_id


class FakeSession:
    def __init__(self, project_id: str | None) -> None:
        self.auth = FakeAuth(project_id)


class FakeConnection:
    def __init__(self, project_id: str | None) -> None:
        self.session = FakeSession(project_id)


def test_project_id_mismatch_stops_synchronization() -> None:
    with pytest.raises(ProjectScopeMismatchError):
        validate_authenticated_project(
            FakeConnection("project-apptest"),
            expected_project_id="project-appdev",
            inventory_scope="appdev",
        )


def test_project_id_validation_allows_unavailable_sdk_scope() -> None:
    assert (
        validate_authenticated_project(
            FakeConnection(None),
            expected_project_id="project-appdev",
            inventory_scope="appdev",
        )
        is None
    )
