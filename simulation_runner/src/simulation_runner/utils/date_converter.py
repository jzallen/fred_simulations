"""
Date format conversion utilities for FRED simulations.

FRED 10 requires dates in the format YYYY-Mon-DD (e.g., 2020-Jan-01),
while EPX and FRED 11+ use ISO format YYYY-MM-DD (e.g., 2020-01-01).

This module provides conversion between these formats.
"""

from datetime import datetime


# Month number to abbreviation mapping for FRED 10
MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


def convert_date_to_fred10_format(date_str: str) -> str:
    """
    Convert ISO date (YYYY-MM-DD) to FRED 10 format (YYYY-Mon-DD).

    Parameters
    ----------
    date_str : str
        Date in ISO format (YYYY-MM-DD)

    Returns
    -------
    str
        Date in FRED 10 format (YYYY-Mon-DD)

    Raises
    ------
    ValueError
        If date_str is not a valid ISO format date

    Examples
    --------
    >>> convert_date_to_fred10_format("2020-01-01")
    '2020-Jan-01'
    >>> convert_date_to_fred10_format("2020-03-31")
    '2020-Mar-31'
    >>> convert_date_to_fred10_format("2020-12-25")
    '2020-Dec-25'
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected YYYY-MM-DD (ISO format)"
        ) from e

    month_abbr = MONTH_ABBR[date_obj.month - 1]
    return f"{date_obj.year}-{month_abbr}-{date_obj.day:02d}"


def convert_date_from_fred10_format(date_str: str) -> str:
    """
    Convert FRED 10 date format (YYYY-Mon-DD) to ISO format (YYYY-MM-DD).

    Parameters
    ----------
    date_str : str
        Date in FRED 10 format (YYYY-Mon-DD)

    Returns
    -------
    str
        Date in ISO format (YYYY-MM-DD)

    Raises
    ------
    ValueError
        If date_str is not a valid FRED 10 format date

    Examples
    --------
    >>> convert_date_from_fred10_format("2020-Jan-01")
    '2020-01-01'
    >>> convert_date_from_fred10_format("2020-Mar-31")
    '2020-03-31'
    """
    # Parse FRED 10 format manually since strptime doesn't support custom month names easily
    parts = date_str.split("-")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid FRED 10 date format: {date_str}. Expected YYYY-Mon-DD"
        )

    year_str, month_str, day_str = parts

    try:
        year = int(year_str)
        day = int(day_str)
    except ValueError as e:
        raise ValueError(
            f"Invalid FRED 10 date format: {date_str}. Year and day must be numeric"
        ) from e

    # Find month number from abbreviation
    try:
        month = MONTH_ABBR.index(month_str) + 1
    except ValueError as e:
        raise ValueError(
            f"Invalid month abbreviation: {month_str}. Expected one of {', '.join(MONTH_ABBR)}"
        ) from e

    # Validate date is valid
    try:
        datetime(year, month, day)
    except ValueError as e:
        raise ValueError(
            f"Invalid date: {date_str} ({year}-{month:02d}-{day:02d})"
        ) from e

    return f"{year}-{month:02d}-{day:02d}"
