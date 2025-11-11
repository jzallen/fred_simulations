import pytest

from epistemix_platform.use_cases.register_job import validate_tags


class TestValidateTagsUseCase:
    def test_validate_tags__with_valid_known_tags__passes_validation(self):
        validate_tags(["info_job"])
        validate_tags(["simulation_job", "analysis_job"])
        validate_tags([])

    def test_validate_tags__when_none_provided__passes_validation(self):
        validate_tags(None)

    def test_validate_tags__when_empty_list__passes_validation(self):
        validate_tags([])

    def test_validate_tags__with_unknown_tags__passes_validation(self):
        validate_tags(["unknown_tag", "custom_tag"])

    def test_validate_tags__when_empty_string__raises_value_error(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([""])

    def test_validate_tags__when_whitespace_only__raises_value_error(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["   "])

    def test_validate_tags__when_non_string_type__raises_value_error(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([123])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([None])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([["nested_list"]])

    def test_validate_tags__when_mixed_valid_invalid__raises_value_error(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["valid_tag", "", "another_valid_tag"])

    def test_validate_tags__with_completely_unknown_tags__allows_flexibility(self):
        try:
            validate_tags(["completely_unknown_tag", "another_unknown"])
        except ValueError:
            pytest.fail("Unknown tags should be allowed per current business rules")
