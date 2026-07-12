"""Application-specific exceptions."""


class InventorySyncError(Exception):
    """Base exception for inventory synchronization failures."""


class ConfigurationError(InventorySyncError):
    """Raised when required configuration is missing or unsupported."""


class InventorySourceConflictError(ConfigurationError):
    """Raised when a configured inventory source conflicts with database state."""


class OpenStackConnectionError(InventorySyncError):
    """Raised when an OpenStack connection cannot be created."""


class ProjectScopeMismatchError(InventorySyncError):
    """Raised when authenticated OpenStack project scope does not match configuration."""


class SourceLockError(InventorySyncError):
    """Raised when another sync already holds the source-specific lock."""


class SyncError(InventorySyncError):
    """Raised when a resource synchronization fails."""
