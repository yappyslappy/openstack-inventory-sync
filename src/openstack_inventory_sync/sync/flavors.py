"""Flavor synchronization."""

from openstack_inventory_sync.models import Flavor
from openstack_inventory_sync.openstack.serializers import serialize_flavor
from openstack_inventory_sync.sync.base import ResourceSync


class FlavorSync(ResourceSync):
    resource_name = "flavors"
    model = Flavor
    list_method_name = "list_flavors"
    serializer = staticmethod(serialize_flavor)
