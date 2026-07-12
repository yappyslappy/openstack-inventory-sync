"""Application-specific exceptions."""


class InventorySyncError(Exception):
    """Base exception for inventory synchronization failures."""


class ConfigurationError(InventorySyncError):
    """Raised when required configuration is missing or unsupported."""


class OpenStackConnectionError(InventorySyncError):
    """Raised when an OpenStack connection cannot be created."""


class SyncError(InventorySyncError):
    """Raised when a resource synchronization fails."""
