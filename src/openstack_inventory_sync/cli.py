"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from sqlalchemy import text

from openstack_inventory_sync.config import AppSettings
from openstack_inventory_sync.database.engine import create_mysql_engine
from openstack_inventory_sync.database.session import create_session_factory
from openstack_inventory_sync.exceptions import ConfigurationError, InventorySyncError
from openstack_inventory_sync.logging_config import configure_logging
from openstack_inventory_sync.openstack.client import OpenStackInventoryClient
from openstack_inventory_sync.openstack.connection import create_openstack_connection
from openstack_inventory_sync.sync.orchestrator import SYNC_CLASSES, SyncOrchestrator

logger = logging.getLogger(__name__)

RESOURCE_NAMES = tuple(sync_class.resource_name for sync_class in SYNC_CLASSES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize OpenStack inventory into MySQL.")
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
        settings = AppSettings.from_env()
        configure_logging(settings.log_level)

        if args.command == "healthcheck":
            return run_healthcheck(settings)
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
    logger.info("healthcheck.ok", extra={"database": settings.mysql.safe_dsn()})
    return 0


def run_sync(settings: AppSettings, *, resource: str, remove_missing: bool) -> int:
    logger.info(
        "sync.configuration_loaded",
        extra={
            "region_name": settings.openstack.region_name,
            "interface": settings.openstack.interface,
            "database": settings.mysql.safe_dsn(),
        },
    )
    engine = create_mysql_engine(settings.mysql)
    session_factory = create_session_factory(engine)
    connection = create_openstack_connection(settings.openstack)
    client = OpenStackInventoryClient(connection)
    orchestrator = SyncOrchestrator(client, session_factory, settings.openstack.region_name)

    if resource == "all":
        results = orchestrator.sync_all(remove_missing=remove_missing)
    else:
        results = [orchestrator.sync_resource(resource, remove_missing=remove_missing)]

    logger.info("sync.completed", extra={"results": [result.as_log_dict() for result in results]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
