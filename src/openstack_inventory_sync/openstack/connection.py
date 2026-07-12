"""OpenStack SDK connection factory."""

from __future__ import annotations

from typing import Any

import openstack

from openstack_inventory_sync import __version__
from openstack_inventory_sync.config import OpenStackSettings
from openstack_inventory_sync.exceptions import OpenStackConnectionError


def create_openstack_connection(settings: OpenStackSettings) -> Any:
    """Create one OpenStack SDK connection using Application Credentials only."""

    try:
        return openstack.connect(
            auth_type="v3applicationcredential",
            auth_url=settings.auth_url,
            application_credential_id=settings.application_credential_id,
            application_credential_secret=settings.application_credential_secret,
            region_name=settings.region_name,
            interface=settings.interface,
            identity_api_version=settings.identity_api_version,
            app_name="openstack-inventory-sync",
            app_version=__version__,
            api_timeout=settings.operation_timeout,
            connect_retries=3,
            status_code_retries=3,
        )
    except Exception:
        raise OpenStackConnectionError("Unable to create OpenStack SDK connection") from None
