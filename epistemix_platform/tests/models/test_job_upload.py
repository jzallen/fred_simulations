"""Tests for JobUpload domain model."""

import pytest

from epistemix_platform.models.job_upload import JobUpload
from epistemix_platform.models.upload_location import UploadLocation


class TestJobUploadGetDefaultFilename:
    """Test JobUpload.get_default_filename() method."""

    def test_job_config_upload_filename(self):
        upload = JobUpload(context="job", upload_type="config", job_id=12)

        filename = upload.get_default_filename()

        assert filename == "job_12_config.json"

    def test_job_input_upload_filename(self):
        upload = JobUpload(context="job", upload_type="input", job_id=42)

        filename = upload.get_default_filename()

        assert filename == "job_42_input.zip"

    def test_run_config_upload_filename(self):
        upload = JobUpload(context="run", upload_type="config", job_id=12, run_id=4)

        filename = upload.get_default_filename()

        assert filename == "run_4_config.json"

    def test_run_output_upload_filename(self):
        upload = JobUpload(context="run", upload_type="output", job_id=12, run_id=7)

        filename = upload.get_default_filename()

        assert filename == "run_7_output.csv"

    def test_run_results_upload_filename(self):
        upload = JobUpload(context="run", upload_type="results", job_id=12, run_id=3)

        filename = upload.get_default_filename()

        assert filename == "run_3_results.csv"

    def test_run_logs_upload_filename(self):
        upload = JobUpload(context="run", upload_type="logs", job_id=12, run_id=5)

        filename = upload.get_default_filename()

        assert filename == "run_5_logs.log"

    def test_run_without_run_id_uses_fallback(self):
        upload = JobUpload(context="run", upload_type="logs", job_id=12)

        filename = upload.get_default_filename()

        assert filename == "run_logs.log"

    def test_unknown_upload_type_uses_txt_extension(self):
        upload = JobUpload(context="job", upload_type="input", job_id=12)
        upload.upload_type = "unknown"

        filename = upload.get_default_filename()

        assert filename == "job_12_unknown.txt"


class TestJobUploadToSanitizedDict:
    """Test JobUpload.to_sanitized_dict() method."""

    def test_to_sanitized_dict_without_location(self):
        upload = JobUpload(context="job", upload_type="config", job_id=12)

        result = upload.to_sanitized_dict()

        assert result == {
            "context": "job",
            "uploadType": "config",
            "jobId": 12,
            "runId": None,
        }

    def test_to_sanitized_dict_with_location(self):
        location = UploadLocation(
            url="https://s3.amazonaws.com/bucket/jobs/12/config.json?AWSAccessKeyId=XXX&Signature=YYY"
        )
        upload = JobUpload(context="job", upload_type="config", job_id=12, location=location)

        result = upload.to_sanitized_dict()

        assert result["context"] == "job"
        assert result["uploadType"] == "config"
        assert result["jobId"] == 12
        assert result["runId"] is None
        assert "location" in result
        assert "?" not in result["location"]["url"]

    def test_to_sanitized_dict_sanitizes_query_parameters(self):
        location = UploadLocation(url="https://example.com/file.json?secret=token123&key=value")
        upload = JobUpload(context="job", upload_type="config", job_id=12, location=location)

        result = upload.to_sanitized_dict()

        assert result["location"]["url"] == "https://example.com/file.json"

    def test_to_sanitized_dict_with_run_context(self):
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/runs/4/output.csv")
        upload = JobUpload(
            context="run", upload_type="output", job_id=12, run_id=4, location=location
        )

        result = upload.to_sanitized_dict()

        assert result == {
            "context": "run",
            "uploadType": "output",
            "jobId": 12,
            "runId": 4,
            "location": {"url": "https://s3.amazonaws.com/bucket/runs/4/output.csv"},
        }


class TestJobUploadRepr:
    """Test JobUpload string representation."""

    def test_repr_without_run_id_or_location(self):
        upload = JobUpload(context="job", upload_type="config", job_id=12)

        repr_str = repr(upload)

        assert "JobUpload(" in repr_str
        assert "context=job" in repr_str
        assert "type=config" in repr_str
        assert "job_id=12" in repr_str
        assert "run_id" not in repr_str
        assert "location" not in repr_str

    def test_repr_with_run_id(self):
        upload = JobUpload(context="run", upload_type="output", job_id=12, run_id=4)

        repr_str = repr(upload)

        assert "JobUpload(" in repr_str
        assert "context=run" in repr_str
        assert "type=output" in repr_str
        assert "job_id=12" in repr_str
        assert "run_id=4" in repr_str

    def test_repr_with_location(self):
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/file.json")
        upload = JobUpload(context="job", upload_type="config", job_id=12, location=location)

        repr_str = repr(upload)

        assert "JobUpload(" in repr_str
        assert "location=https://s3.amazonaws.com/bucket/file.json" in repr_str

    def test_repr_with_run_id_and_location(self):
        location = UploadLocation(url="https://example.com/output.csv")
        upload = JobUpload(
            context="run", upload_type="output", job_id=12, run_id=4, location=location
        )

        repr_str = repr(upload)

        assert "run_id=4" in repr_str
        assert "location=https://example.com/output.csv" in repr_str
