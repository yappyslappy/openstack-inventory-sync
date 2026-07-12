"""Network synchronization."""

from openstack_inventory_sync.models import Network
from openstack_inventory_sync.openstack.serializers import serialize_network
from openstack_inventory_sync.sync.base import ResourceSync


class NetworkSync(ResourceSync):
    resource_name = "networks"
    model = Network
    list_method_name = "list_networks"
    serializer = staticmethod(serialize_network)
