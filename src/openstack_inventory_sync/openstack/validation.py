"""OpenStack authenticated project-scope validation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from openstack_inventory_sync.exceptions import ProjectScopeMismatchError

logger = logging.getLogger(__name__)


def validate_authenticated_project(
    connection: Any,
    *,
    expected_project_id: str,
    inventory_scope: str,
) -> str | None:
    """Validate the authenticated project ID when the SDK can expose it safely."""

    authenticated_project_id = determine_authenticated_project_id(connection)
    if authenticated_project_id is None:
        logger.warning(
            "openstack_project_validation.unavailable",
            extra={
                "inventory_scope": inventory_scope,
                "openstack_project_id": expected_project_id,
            },
        )
        return None

    if authenticated_project_id != expected_project_id:
        logger.error(
            "openstack_project_validation.mismatch",
            extra={
                "inventory_scope": inventory_scope,
                "openstack_project_id": expected_project_id,
                "authenticated_project_id": authenticated_project_id,
            },
        )
        raise ProjectScopeMismatchError(
            "Authenticated OpenStack project does not match configuration"
        )

    logger.info(
        "openstack_project_validation.ok",
        extra={
            "inventory_scope": inventory_scope,
            "openstack_project_id": expected_project_id,
        },
    )
    return authenticated_project_id


def determine_authenticated_project_id(connection: Any) -> str | None:
    """Best-effort project ID extraction without exposing tokens."""

    session = getattr(connection, "session", None)
    auth = getattr(session, "auth", None)

    for candidate in (
        _project_id_from_auth_get_project_id(auth, session),
        _project_id_from_session_get_project_id(session),
        _project_id_from_auth_access(auth, session),
        _project_id_from_connection_config(connection),
    ):
        if candidate:
            return candidate
    return None


def _project_id_from_auth_get_project_id(auth: Any, session: Any) -> str | None:
    if auth is None or not hasattr(auth, "get_project_id"):
        return None
    try:
        project_id = auth.get_project_id(session)
    except Exception:
        return None
    return str(project_id) if project_id else None


def _project_id_from_session_get_project_id(session: Any) -> str | None:
    if session is None or not hasattr(session, "get_project_id"):
        return None
    try:
        project_id = session.get_project_id()
    except Exception:
        return None
    return str(project_id) if project_id else None


def _project_id_from_auth_access(auth: Any, session: Any) -> str | None:
    if auth is None or not hasattr(auth, "get_access"):
        return None
    try:
        access = auth.get_access(session)
    except Exception:
        return None

    for attr_name in ("project_id", "project_id_from_token"):
        project_id = getattr(access, attr_name, None)
        if project_id:
            return str(project_id)

    project = getattr(access, "project", None)
    if isinstance(project, Mapping):
        project_id = project.get("id")
        return str(project_id) if project_id else None
    return None


def _project_id_from_connection_config(connection: Any) -> str | None:
    config = getattr(connection, "config", None)
    auth = getattr(config, "auth", None)
    if isinstance(auth, Mapping):
        project_id = auth.get("project_id")
        return str(project_id) if project_id else None
    return None
