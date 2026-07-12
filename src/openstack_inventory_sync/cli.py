"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openstack_inventory_sync.config import AppSettings
from openstack_inventory_sync.database.engine import create_mysql_engine
from openstack_inventory_sync.database.session import create_session_factory, transactional_session
from openstack_inventory_sync.exceptions import ConfigurationError, InventorySyncError
from openstack_inventory_sync.logging_config import configure_logging
from openstack_inventory_sync.openstack.client import OpenStackInventoryClient
from openstack_inventory_sync.openstack.connection import create_openstack_connection
from openstack_inventory_sync.openstack.validation import validate_authenticated_project
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.context import InventorySourceContext
from openstack_inventory_sync.sync.locking import source_lock
from openstack_inventory_sync.sync.orchestrator import SYNC_CLASSES, SyncOrchestrator

logger = logging.getLogger(__name__)

RESOURCE_NAMES = tuple(sync_class.resource_name for sync_class in SYNC_CLASSES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize OpenStack inventory into MySQL.")
    parser.add_argument(
        "--env-file",
        help="Load configuration from an explicit dotenv file. Shell environment values override it.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Synchronize inventory.")
    sync_parser.add_argument(
        "resource",
        nargs="?",
        default="all",
        choices=("all", *RESOURCE_NAMES),
        help="Resource type to sync. Defaults to all resources.",
    )
    sync_parser.add_argument(
        "--remove-missing",
        action="store_true",
        help="Delete missing rows instead of marking them deleted.",
    )

    subparsers.add_parser("list-resources", help="Print supported resource names.")
    subparsers.add_parser("healthcheck", help="Validate configuration and database connectivity.")
    subparsers.add_parser(
        "validate-config",
        help="Validate environment, database access, source mapping, and OpenStack project scope.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-resources":
        for resource_name in RESOURCE_NAMES:
            print(resource_name)
        return 0

    try:
        settings = AppSettings.from_env(env_file=args.env_file)
        configure_logging(settings.log_level)

        if args.command == "healthcheck":
            return run_healthcheck(settings)
        if args.command == "validate-config":
            return run_validate_config(settings)
        if args.command == "sync":
            return run_sync(settings, resource=args.resource, remove_missing=args.remove_missing)
    except ConfigurationError as exc:
        logger.error("configuration_error", extra={"error": str(exc)})
        return 2
    except InventorySyncError as exc:
        logger.error("inventory_sync_error", extra={"error": str(exc)})
        return 1
    except Exception:
        logger.error("unexpected_error", extra={"error": "Unhandled failure"})
        return 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


def run_healthcheck(settings: AppSettings) -> int:
    engine = create_mysql_engine(settings.mysql)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info(
        "healthcheck.ok",
        extra={
            "database": settings.mysql.safe_dsn(),
            "inventory_scope": settings.inventory.scope_key,
            "openstack_project_id": settings.inventory.openstack_project_id,
            "openstack_project_name": settings.inventory.openstack_project_name,
        },
    )
    return 0


def run_validate_config(settings: AppSettings) -> int:
    engine = create_mysql_engine(settings.mysql)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    session_factory = create_session_factory(engine)
    with transactional_session(session_factory) as session:
        InventoryRepository(session).validate_inventory_source_mapping(
            scope_key=settings.inventory.scope_key,
            openstack_project_id=settings.inventory.openstack_project_id,
            region_name=settings.openstack.region_name,
            auth_url=settings.openstack.auth_url,
        )

    connection = create_openstack_connection(settings.openstack)
    validate_authenticated_project(
        connection,
        expected_project_id=settings.inventory.openstack_project_id,
        inventory_scope=settings.inventory.scope_key,
    )
    logger.info(
        "validate_config.ok",
        extra={
            "inventory_scope": settings.inventory.scope_key,
            "openstack_project_id": settings.inventory.openstack_project_id,
            "openstack_project_name": settings.inventory.openstack_project_name,
            "database": settings.mysql.safe_dsn(),
        },
    )
    return 0


def run_sync(settings: AppSettings, *, resource: str, remove_missing: bool) -> int:
    logger.info(
        "sync.configuration_loaded",
        extra={
            "inventory_scope": settings.inventory.scope_key,
            "openstack_project_id": settings.inventory.openstack_project_id,
            "openstack_project_name": settings.inventory.openstack_project_name,
            "region_name": settings.openstack.region_name,
            "interface": settings.openstack.interface,
            "database": settings.mysql.safe_dsn(),
        },
    )

    with source_lock(settings.inventory.scope_key, settings.inventory.lock_dir) as lock_path:
        logger.info(
            "sync.lock_acquired",
            extra={
                "inventory_scope": settings.inventory.scope_key,
                "lock_path": str(lock_path),
            },
        )
        engine = create_mysql_engine(settings.mysql)
        session_factory = create_session_factory(engine)
        connection = create_openstack_connection(settings.openstack)
        validate_authenticated_project(
            connection,
            expected_project_id=settings.inventory.openstack_project_id,
            inventory_scope=settings.inventory.scope_key,
        )
        source_context = ensure_source_context(settings, session_factory)
        client = OpenStackInventoryClient(connection)
        orchestrator = SyncOrchestrator(client, session_factory, source_context)

        try:
            if resource == "all":
                results = orchestrator.sync_all(remove_missing=remove_missing)
            else:
                results = [orchestrator.sync_resource(resource, remove_missing=remove_missing)]
        except Exception:
            mark_source_failure(session_factory, source_context)
            raise
        mark_source_success(session_factory, source_context)

    logger.info(
        "sync.completed",
        extra={
            "inventory_scope": settings.inventory.scope_key,
            "openstack_project_id": settings.inventory.openstack_project_id,
            "openstack_project_name": settings.inventory.openstack_project_name,
            "results": [result.as_log_dict() for result in results],
        },
    )
    return 0


def ensure_source_context(
    settings: AppSettings, session_factory: sessionmaker[Session]
) -> InventorySourceContext:
    with transactional_session(session_factory) as session:
        source = InventoryRepository(session).ensure_inventory_source(
            scope_key=settings.inventory.scope_key,
            openstack_project_id=settings.inventory.openstack_project_id,
            openstack_project_name=settings.inventory.openstack_project_name,
            region_name=settings.openstack.region_name,
            auth_url=settings.openstack.auth_url,
        )
        logger.info(
            "inventory_source.ready",
            extra={
                "inventory_scope": source.context.scope_key,
                "openstack_project_id": source.context.openstack_project_id,
                "openstack_project_name": source.context.openstack_project_name,
                "created": source.created,
            },
        )
        return source.context


def mark_source_success(
    session_factory: sessionmaker[Session], source: InventorySourceContext
) -> None:
    with transactional_session(session_factory) as session:
        InventoryRepository(session).mark_source_success(source)


def mark_source_failure(
    session_factory: sessionmaker[Session], source: InventorySourceContext
) -> None:
    with transactional_session(session_factory) as session:
        InventoryRepository(session).mark_source_failure(source)


if __name__ == "__main__":
    sys.exit(main())
