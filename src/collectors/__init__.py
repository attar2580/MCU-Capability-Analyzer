class CollectorError(Exception):
    """Base exception for all collector errors."""


class BoardCollectorError(CollectorError):
    """Board collector-specific errors."""


class MCUCollectorError(CollectorError):
    """MCU collector-specific errors."""


class SDKCollectorError(CollectorError):
    """SDK collector-specific errors."""
