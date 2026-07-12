"""Subnet synchronization."""

from openstack_inventory_sync.models import Subnet
from openstack_inventory_sync.openstack.serializers import serialize_subnet
from openstack_inventory_sync.sync.base import ResourceSync


class SubnetSync(ResourceSync):
    resource_name = "subnets"
    model = Subnet
    list_method_name = "list_subnets"
    serializer = staticmethod(serialize_subnet)
