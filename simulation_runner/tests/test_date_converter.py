"""
Tests for date conversion utilities.
"""

import pytest

from simulation_runner.utils.date_converter import (
    convert_date_from_fred10_format,
    convert_date_to_fred10_format,
)


class TestDateConversion:
    """Tests for date format conversion functions."""

    def test_convert_to_fred10_january(self):
        """Test converting January date to FRED 10 format."""
        result = convert_date_to_fred10_format("2020-01-01")
        assert result == "2020-Jan-01"

    def test_convert_to_fred10_march(self):
        """Test converting March date to FRED 10 format."""
        result = convert_date_to_fred10_format("2020-03-31")
        assert result == "2020-Mar-31"

    def test_convert_to_fred10_december(self):
        """Test converting December date to FRED 10 format."""
        result = convert_date_to_fred10_format("2020-12-25")
        assert result == "2020-Dec-25"

    def test_convert_to_fred10_invalid_format(self):
        """Test error handling for invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            convert_date_to_fred10_format("2020/01/01")

    def test_convert_to_fred10_invalid_date(self):
        """Test error handling for invalid date."""
        with pytest.raises(ValueError, match="Invalid date format"):
            convert_date_to_fred10_format("2020-13-01")  # Invalid month

    def test_convert_from_fred10_january(self):
        """Test converting January date from FRED 10 format."""
        result = convert_date_from_fred10_format("2020-Jan-01")
        assert result == "2020-01-01"

    def test_convert_from_fred10_march(self):
        """Test converting March date from FRED 10 format."""
        result = convert_date_from_fred10_format("2020-Mar-31")
        assert result == "2020-03-31"

    def test_convert_from_fred10_december(self):
        """Test converting December date from FRED 10 format."""
        result = convert_date_from_fred10_format("2020-Dec-25")
        assert result == "2020-12-25"

    def test_convert_from_fred10_invalid_month(self):
        """Test error handling for invalid month abbreviation."""
        with pytest.raises(ValueError, match="Invalid month abbreviation"):
            convert_date_from_fred10_format("2020-Foo-01")

    def test_convert_from_fred10_invalid_format(self):
        """Test error handling for invalid format."""
        with pytest.raises(ValueError, match="Invalid FRED 10 date format"):
            convert_date_from_fred10_format("2020/Jan/01")

    def test_roundtrip_conversion(self):
        """Test that converting to and from FRED 10 format is lossless."""
        original = "2020-03-15"
        fred10 = convert_date_to_fred10_format(original)
        back_to_iso = convert_date_from_fred10_format(fred10)
        assert back_to_iso == original
