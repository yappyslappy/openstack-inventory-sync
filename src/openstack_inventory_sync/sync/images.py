"""Image synchronization."""

from openstack_inventory_sync.models import Image
from openstack_inventory_sync.openstack.serializers import serialize_image
from openstack_inventory_sync.sync.base import ResourceSync


class ImageSync(ResourceSync):
    resource_name = "images"
    model = Image
    list_method_name = "list_images"
    serializer = staticmethod(serialize_image)
