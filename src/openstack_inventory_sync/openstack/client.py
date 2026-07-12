"""OpenStack inventory client facade."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast


class OpenStackInventoryClient:
    """Thin wrapper around a single OpenStack SDK connection."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def list_projects(self) -> list[Any]:
        return list(self.connection.identity.projects())

    def list_flavors(self) -> list[Any]:
        return list(self._call_proxy("compute", "flavors", details=True))

    def list_images(self) -> list[Any]:
        return list(self.connection.image.images())

    def list_networks(self) -> list[Any]:
        return list(self.connection.network.networks())

    def list_subnets(self) -> list[Any]:
        return list(self.connection.network.subnets())

    def list_ports(self) -> list[Any]:
        return list(self.connection.network.ports())

    def list_servers(self) -> list[Any]:
        return list(self._call_proxy("compute", "servers", details=True))

    def list_volumes(self) -> list[Any]:
        return list(self._call_proxy("block_storage", "volumes", details=True))

    def list_floating_ips(self) -> list[Any]:
        if hasattr(self.connection.network, "ips"):
            return list(self.connection.network.ips())
        return list(self.connection.network.floating_ips())

    def list_security_groups(self) -> list[Any]:
        return list(self.connection.network.security_groups())

    def _call_proxy(self, proxy_name: str, method_name: str, **kwargs: Any) -> Iterable[Any]:
        proxy = getattr(self.connection, proxy_name)
        method = getattr(proxy, method_name)
        try:
            return cast(Iterable[Any], method(**kwargs))
        except TypeError:
            return cast(Iterable[Any], method())
