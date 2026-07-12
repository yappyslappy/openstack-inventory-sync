"""Volume synchronization."""

from openstack_inventory_sync.models import Volume, VolumeAttachment
from openstack_inventory_sync.openstack.serializers import (
    serialize_volume,
    serialize_volume_attachments,
)
from openstack_inventory_sync.repositories.inventory import InventoryRepository
from openstack_inventory_sync.sync.base import ResourcePayload, ResourceSync


class VolumeSync(ResourceSync):
    resource_name = "volumes"
    model = Volume
    list_method_name = "list_volumes"
    serializer = staticmethod(serialize_volume)

    def sync_child_records(
        self, repository: InventoryRepository, accepted: list[ResourcePayload]
    ) -> None:
        parent_ids = {payload["id"] for _, payload in accepted}
        repository.replace_child_records(
            VolumeAttachment,
            [row for resource, _ in accepted for row in serialize_volume_attachments(resource)],
            source=self.source,
            parent_field="volume_id",
            parent_ids=parent_ids,
        )
