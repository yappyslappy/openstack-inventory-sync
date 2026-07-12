"""Volume synchronization."""

from openstack_inventory_sync.models import Volume
from openstack_inventory_sync.openstack.serializers import serialize_volume
from openstack_inventory_sync.sync.base import ResourceSync


class VolumeSync(ResourceSync):
    resource_name = "volumes"
    model = Volume
    list_method_name = "list_volumes"
    serializer = staticmethod(serialize_volume)
