"""Project synchronization."""

from openstack_inventory_sync.models import Project
from openstack_inventory_sync.openstack.serializers import serialize_project
from openstack_inventory_sync.sync.base import ResourceSync


class ProjectSync(ResourceSync):
    resource_name = "projects"
    model = Project
    list_method_name = "list_projects"
    serializer = staticmethod(serialize_project)

    def reject_payload(self, payload: dict[str, object]) -> bool:
        return str(payload.get("id")) != self.source.openstack_project_id
