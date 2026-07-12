"""Floating IP synchronization."""

from openstack_inventory_sync.models import FloatingIP
from openstack_inventory_sync.openstack.serializers import serialize_floating_ip
from openstack_inventory_sync.sync.base import ResourceSync


class FloatingIPSync(ResourceSync):
    resource_name = "floating_ips"
    model = FloatingIP
    list_method_name = "list_floating_ips"
    serializer = staticmethod(serialize_floating_ip)
