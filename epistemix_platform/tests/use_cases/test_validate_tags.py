import pytest

from epistemix_platform.use_cases.register_job import validate_tags


class TestValidateTagsUseCase:
    def test_validate_tags_valid_known_tags(self):
        validate_tags(["info_job"])
        validate_tags(["simulation_job", "analysis_job"])
        validate_tags([])

    def test_validate_tags_none_input(self):
        validate_tags(None)

    def test_validate_tags_empty_list(self):
        validate_tags([])

    def test_validate_tags_unknown_tags_allowed(self):
        validate_tags(["unknown_tag", "custom_tag"])

    def test_validate_tags_empty_string(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([""])

    def test_validate_tags_whitespace_only(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["   "])

    def test_validate_tags_non_string_type(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([123])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([None])

        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags([["nested_list"]])

    def test_validate_tags_mixed_valid_invalid(self):
        with pytest.raises(ValueError, match="Tag must be a non-empty string"):
            validate_tags(["valid_tag", "", "another_valid_tag"])

    def test_validate_tags_business_rule_flexibility(self):
        try:
            validate_tags(["completely_unknown_tag", "another_unknown"])
        except ValueError:
            pytest.fail("Unknown tags should be allowed per current business rules")
