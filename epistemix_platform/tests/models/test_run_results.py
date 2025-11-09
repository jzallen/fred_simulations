from epistemix_platform.models.run_results import RunResults


class TestRunResults:
    """Tests for RunResults domain model."""

    def test_to_dict__returns_correct_structure(self):
        """Test that to_dict serializes correctly."""
        run_results = RunResults(
            run_id=42,
            url="https://s3.amazonaws.com/bucket/presigned-url?X-Amz-Expires=86400",
        )

        result = run_results.to_dict()

        assert result == {
            "run_id": 42,
            "url": "https://s3.amazonaws.com/bucket/presigned-url?X-Amz-Expires=86400",
        }

    def test_to_dict__preserves_types(self):
        """Test that to_dict maintains proper types."""
        run_results = RunResults(run_id=1, url="https://example.com")

        result = run_results.to_dict()

        assert isinstance(result["run_id"], int)
        assert isinstance(result["url"], str)

    def test_equality(self):
        """Test that RunResults with same values are equal."""
        result1 = RunResults(run_id=1, url="https://example.com")
        result2 = RunResults(run_id=1, url="https://example.com")

        assert result1 == result2

    def test_inequality__different_run_id(self):
        """Test that RunResults with different run_id are not equal."""
        result1 = RunResults(run_id=1, url="https://example.com")
        result2 = RunResults(run_id=2, url="https://example.com")

        assert result1 != result2

    def test_inequality__different_url(self):
        """Test that RunResults with different url are not equal."""
        result1 = RunResults(run_id=1, url="https://example.com/1")
        result2 = RunResults(run_id=1, url="https://example.com/2")

        assert result1 != result2
