"""
Time provider service for the Epistemix platform.

This module provides abstractions for time/clock operations, enabling
testable time-dependent behavior without relying on system clock.

Following clean architecture principles, time is treated as an external
dependency that should be injected rather than directly accessed.
"""

from datetime import datetime
from typing import Protocol


class ITimeProvider(Protocol):
    """
    Protocol (interface) for time/clock operations.

    This abstraction allows use cases and services to work with time
    without depending on the system clock, making time-dependent behavior
    fully testable.
    """

    def now_utc(self) -> datetime:
        """
        Get current UTC datetime.

        Returns:
            Current datetime in UTC timezone
        """
        ...


class SystemTimeProvider:
    """
    Production time provider using system clock.

    This implementation delegates to Python's datetime.utcnow() to provide
    real system time in UTC.
    """

    def now_utc(self) -> datetime:
        """
        Get current system time in UTC.

        Returns:
            Current system datetime in UTC timezone
        """
        return datetime.utcnow()


class FixedTimeProvider:
    """
    Test time provider with fixed datetime.

    This implementation always returns the same fixed datetime, allowing
    tests to verify exact timestamps without race conditions or timing issues.

    Example:
        >>> fixed_time = datetime(2025, 10, 23, 19, 56, 0)
        >>> provider = FixedTimeProvider(fixed_time)
        >>> provider.now_utc()
        datetime.datetime(2025, 10, 23, 19, 56, 0)
        >>> provider.now_utc()  # Always returns same value
        datetime.datetime(2025, 10, 23, 19, 56, 0)
    """

    def __init__(self, fixed_time: datetime):
        """
        Initialize with a fixed datetime.

        Args:
            fixed_time: The datetime to always return from now_utc()
        """
        self._time = fixed_time

    def now_utc(self) -> datetime:
        """
        Get the fixed datetime.

        Returns:
            The fixed datetime set during initialization
        """
        return self._time
