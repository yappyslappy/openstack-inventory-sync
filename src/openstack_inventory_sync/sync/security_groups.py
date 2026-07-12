"""Security group synchronization."""

from openstack_inventory_sync.models import SecurityGroup
from openstack_inventory_sync.openstack.serializers import serialize_security_group
from openstack_inventory_sync.sync.base import ResourceSync


class SecurityGroupSync(ResourceSync):
    resource_name = "security_groups"
    model = SecurityGroup
    list_method_name = "list_security_groups"
    serializer = staticmethod(serialize_security_group)
