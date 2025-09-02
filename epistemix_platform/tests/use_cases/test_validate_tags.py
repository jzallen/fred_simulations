"""
Tests for validate_tags use case.
"""

import pytest

from epistemix_platform.use_cases.register_job import validate_tags


class TestValidateTagsUseCase:
    """Test the validate_tags use case."""

    def test_validate_tags_valid_known_tags(self):
        """Test validation with known valid tags."""
        # These should not raise any exceptions
        validate_tags(["info_job"])
        validate_tags(["simulation_job", "analysis_job"])
        validate_tags([])  # Empty list should be valid

    def test_validate_tags_none_input(self):
        """Test validation with None input."""
        # Should not raise exception
        validate_tags(None)

    def test_validate_tags_empty_list(self):
        """Test validation with empty list."""
        # Should not raise exception
        validate_tags([])

    def test_validate_tags_unknown_tags_allowed(self):
        """Test that unknown tags are currently allowed."""
        # This should not raise an exception (current business rule)
        validate_tags(["unknown_tag", "custom_tag"])

    def test_validate_tags_empty_string(self):
        """Test validation with empty string tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([""])

    def test_validate_tags_whitespace_only(self):
        """Test validation with whitespace-only tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["   "])

    def test_validate_tags_non_string_type(self):
        """Test validation with non-string tag."""
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([123])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([None])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([["nested_list"]])

    def test_validate_tags_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid tags."""
        # Should fail on the first invalid tag
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["valid_tag", "", "another_valid_tag"])

    def test_validate_tags_business_rule_flexibility(self):
        """Test that validation follows current business rules."""
        # Current business rule: allow unknown tags
        # This test documents the current behavior
        try:
            validate_tags(["completely_unknown_tag", "another_unknown"])
            # If we reach here, unknown tags are allowed (current behavior)
        except ValueError:
            # If this raises ValueError, strict validation is enabled
            pytest.fail("Unknown tags should be allowed per current business rules")
