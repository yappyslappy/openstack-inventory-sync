from __future__ import annotations

import pytest

from openstack_inventory_sync.config import (
    REQUIRED_MYSQL_ENV,
    REQUIRED_OPENSTACK_ENV,
    UNSUPPORTED_OPENSTACK_ENV,
    MySQLSettings,
    OpenStackSettings,
)
from openstack_inventory_sync.exceptions import ConfigurationError


def clear_relevant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        *REQUIRED_OPENSTACK_ENV,
        *UNSUPPORTED_OPENSTACK_ENV,
        *REQUIRED_MYSQL_ENV,
        "OS_REGION_NAME",
        "OS_INTERFACE",
        "OS_IDENTITY_API_VERSION",
        "MYSQL_PORT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_openstack_settings_require_application_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_relevant_env(monkeypatch)
    monkeypatch.setenv("OS_AUTH_URL", "https://identity.example/v3")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_ID", "credential-id")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_SECRET", "secret")

    settings = OpenStackSettings.from_env()

    assert settings.auth_url == "https://identity.example/v3"
    assert settings.region_name == "RegionOne"
    assert settings.interface == "internal"
    assert settings.safe_dict()["application_credential_secret"] == "***"


def test_openstack_settings_reject_username_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_relevant_env(monkeypatch)
    monkeypatch.setenv("OS_AUTH_URL", "https://identity.example/v3")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_ID", "credential-id")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_SECRET", "secret")
    monkeypatch.setenv("OS_USERNAME", "someone")

    with pytest.raises(ConfigurationError, match="Application Credentials"):
        OpenStackSettings.from_env()


def test_openstack_settings_require_identity_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_relevant_env(monkeypatch)
    monkeypatch.setenv("OS_AUTH_URL", "https://identity.example/v3")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_ID", "credential-id")
    monkeypatch.setenv("OS_APPLICATION_CREDENTIAL_SECRET", "secret")
    monkeypatch.setenv("OS_IDENTITY_API_VERSION", "2")

    with pytest.raises(ConfigurationError, match="OS_IDENTITY_API_VERSION"):
        OpenStackSettings.from_env()


def test_mysql_settings_build_safe_sqlalchemy_url(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_relevant_env(monkeypatch)
    monkeypatch.setenv("MYSQL_HOST", "db.example")
    monkeypatch.setenv("MYSQL_DATABASE", "inventory")
    monkeypatch.setenv("MYSQL_USERNAME", "sync_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "super-secret")

    settings = MySQLSettings.from_env()

    assert settings.sqlalchemy_url().drivername == "mysql+pymysql"
    assert "super-secret" not in settings.safe_dsn()
    assert "***" in settings.safe_dsn()


def test_mysql_settings_validate_integer_values(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_relevant_env(monkeypatch)
    monkeypatch.setenv("MYSQL_HOST", "db.example")
    monkeypatch.setenv("MYSQL_DATABASE", "inventory")
    monkeypatch.setenv("MYSQL_USERNAME", "sync_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "super-secret")
    monkeypatch.setenv("MYSQL_PORT", "not-a-number")

    with pytest.raises(ConfigurationError, match="MYSQL_PORT"):
        MySQLSettings.from_env()


def test_required_environment_lists_do_not_include_password_auth_names() -> None:
    assert "OS_USERNAME" not in REQUIRED_OPENSTACK_ENV
    assert "OS_PASSWORD" not in REQUIRED_OPENSTACK_ENV
