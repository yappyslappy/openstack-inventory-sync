"""Port synchronization."""

from openstack_inventory_sync.models import Port
from openstack_inventory_sync.openstack.serializers import serialize_port
from openstack_inventory_sync.sync.base import ResourceSync


class PortSync(ResourceSync):
    resource_name = "ports"
    model = Port
    list_method_name = "list_ports"
    serializer = staticmethod(serialize_port)
