"""
Services package for the Epistemix platform.

This package contains application services that encapsulate business logic
and coordinate between domain models and infrastructure.
"""

from epistemix_platform.services.results_packager import (
    FredResultsPackager,
    IResultsPackager,
    PackagedResults,
)
from epistemix_platform.services.time_provider import (
    FixedTimeProvider,
    ITimeProvider,
    SystemTimeProvider,
)

__all__ = [
    # Time Provider
    "ITimeProvider",
    "SystemTimeProvider",
    "FixedTimeProvider",
    # Results Packager
    "IResultsPackager",
    "FredResultsPackager",
    "PackagedResults",
]
