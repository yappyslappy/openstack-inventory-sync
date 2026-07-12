"""SQLAlchemy engine factory."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from openstack_inventory_sync.config import MySQLSettings


def create_mysql_engine(settings: MySQLSettings) -> Engine:
    """Create a configured MySQL SQLAlchemy engine."""

    return create_engine(
        settings.sqlalchemy_url(),
        pool_pre_ping=True,
        pool_recycle=settings.pool_recycle,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        future=True,
    )
