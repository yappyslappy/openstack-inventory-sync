"""Security group synchronization."""

from openstack_inventory_sync.models import SecurityGroup, SecurityGroupRule
from openstack_inventory_sync.openstack.serializers import (
    serialize_security_group,
    serialize_security_group_rules,
)
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.base import ResourcePayload, ResourceSync


class SecurityGroupSync(ResourceSync):
    resource_name = "security_groups"
    model = SecurityGroup
    list_method_name = "list_security_groups"
    serializer = staticmethod(serialize_security_group)

    def sync_child_records(
        self, repository: InventoryRepository, accepted: list[ResourcePayload]
    ) -> None:
        parent_ids = {payload["id"] for _, payload in accepted}
        repository.replace_child_records(
            SecurityGroupRule,
            [row for resource, _ in accepted for row in serialize_security_group_rules(resource)],
            source=self.source,
            parent_field="security_group_id",
            parent_ids=parent_ids,
        )
