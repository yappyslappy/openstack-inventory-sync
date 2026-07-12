"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy.engine import URL

from openstack_inventory_sync.exceptions import ConfigurationError

REQUIRED_OPENSTACK_ENV = (
    "OS_AUTH_URL",
    "OS_APPLICATION_CREDENTIAL_ID",
    "OS_APPLICATION_CREDENTIAL_SECRET",
)

UNSUPPORTED_OPENSTACK_ENV = (
    "OS_USERNAME",
    "OS_PASSWORD",
    "OS_PROJECT_NAME",
    "OS_PROJECT_ID",
    "OS_TENANT_NAME",
    "OS_TENANT_ID",
    "OS_USER_DOMAIN_ID",
    "OS_USER_DOMAIN_NAME",
    "OS_PROJECT_DOMAIN_ID",
    "OS_PROJECT_DOMAIN_NAME",
)

REQUIRED_MYSQL_ENV = (
    "MYSQL_HOST",
    "MYSQL_DATABASE",
    "MYSQL_USERNAME",
    "MYSQL_PASSWORD",
)


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _get_int(name: str, default: int, minimum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be greater than or equal to {minimum}")
    return value


@dataclass(frozen=True)
class OpenStackSettings:
    """OpenStack Application Credential settings."""

    auth_url: str
    application_credential_id: str
    application_credential_secret: str
    region_name: str = "RegionOne"
    interface: str = "internal"
    identity_api_version: str = "3"
    connect_timeout: int = 30
    operation_timeout: int = 60

    @classmethod
    def from_env(cls) -> OpenStackSettings:
        unsupported = [name for name in UNSUPPORTED_OPENSTACK_ENV if os.getenv(name)]
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ConfigurationError(
                "Unsupported OpenStack environment variables are set: "
                f"{names}. This service only supports Application Credentials."
            )

        for name in REQUIRED_OPENSTACK_ENV:
            _get_required(name)

        identity_api_version = os.getenv("OS_IDENTITY_API_VERSION", "3")
        if identity_api_version != "3":
            raise ConfigurationError("OS_IDENTITY_API_VERSION must be 3")

        return cls(
            auth_url=_get_required("OS_AUTH_URL"),
            application_credential_id=_get_required("OS_APPLICATION_CREDENTIAL_ID"),
            application_credential_secret=_get_required("OS_APPLICATION_CREDENTIAL_SECRET"),
            region_name=os.getenv("OS_REGION_NAME", "RegionOne"),
            interface=os.getenv("OS_INTERFACE", "internal"),
            identity_api_version=identity_api_version,
            connect_timeout=_get_int("OS_CONNECT_TIMEOUT", 30, minimum=1),
            operation_timeout=_get_int("OS_OPERATION_TIMEOUT", 60, minimum=1),
        )

    def safe_dict(self) -> dict[str, str | int]:
        """Return settings safe for logs."""

        return {
            "auth_url": self.auth_url,
            "region_name": self.region_name,
            "interface": self.interface,
            "identity_api_version": self.identity_api_version,
            "connect_timeout": self.connect_timeout,
            "operation_timeout": self.operation_timeout,
            "application_credential_id": self.application_credential_id,
            "application_credential_secret": "***",
        }


@dataclass(frozen=True)
class MySQLSettings:
    """MySQL connection settings."""

    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str = "utf8mb4"
    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 1800

    @classmethod
    def from_env(cls) -> MySQLSettings:
        for name in REQUIRED_MYSQL_ENV:
            _get_required(name)

        return cls(
            host=_get_required("MYSQL_HOST"),
            port=_get_int("MYSQL_PORT", 3306, minimum=1),
            database=_get_required("MYSQL_DATABASE"),
            username=_get_required("MYSQL_USERNAME"),
            password=_get_required("MYSQL_PASSWORD"),
            charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
            pool_size=_get_int("MYSQL_POOL_SIZE", 5, minimum=1),
            max_overflow=_get_int("MYSQL_MAX_OVERFLOW", 10, minimum=0),
            pool_recycle=_get_int("MYSQL_POOL_RECYCLE", 1800, minimum=1),
        )

    def sqlalchemy_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query={"charset": self.charset},
        )

    def safe_dsn(self) -> str:
        return str(self.sqlalchemy_url().render_as_string(hide_password=True))


@dataclass(frozen=True)
class AppSettings:
    """Top-level application settings."""

    openstack: OpenStackSettings
    mysql: MySQLSettings
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, load_dotenv_file: bool = True) -> AppSettings:
        if load_dotenv_file:
            load_dotenv()
        return cls(
            openstack=OpenStackSettings.from_env(),
            mysql=MySQLSettings.from_env(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
