"""Server synchronization."""

from openstack_inventory_sync.models import Server
from openstack_inventory_sync.openstack.serializers import serialize_server
from openstack_inventory_sync.sync.base import ResourceSync


class ServerSync(ResourceSync):
    resource_name = "servers"
    model = Server
    list_method_name = "list_servers"
    serializer = staticmethod(serialize_server)
