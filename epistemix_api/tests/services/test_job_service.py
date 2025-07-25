"""
Tests for the refactored Flask app using Clean Architecture.
"""

import pytest
from unittest.mock import Mock

from freezegun import freeze_time
from returns.pipeline import is_successful

from epistemix_api.services.job_service import JobService, JobServiceDependencies
from epistemix_api.models.job import Job, JobStatus


@pytest.fixture
def service():
    with freeze_time("2025-01-01 12:00:00"):
        job = Job.create_persisted(job_id=1, user_id=456, tags=["info_job"])

    service = JobService()
    service._dependencies = JobServiceDependencies(
        register_job_fn=Mock(return_value=job),
        submit_job_fn=Mock(return_value={"url": "http://example.com/pre-signed-url", "status": "submitted"}),
        get_job_fn=Mock()
    )
    return service

class TestJobService:
    
    def test_register_job__calls_register_job_fn_with_created_job(self, service):
        service.register_job(user_id=456, tags=["info_job"])
        service._dependencies.register_job_fn.assert_called_once_with(user_id=456, tags=["info_job"])

    def test_register_job__returns_success_result_with_job_data(self, service):
        job_result = service.register_job(user_id=456, tags=["info_job"])
        assert is_successful(job_result)
        expected_job_data = {
            "id": 1,
            "userId": 456,
            "tags": ["info_job"],
            "status": JobStatus.CREATED.value,
            "createdAt": "2025-01-01T12:00:00",
            "updatedAt": "2025-01-01T12:00:00",
            "metadata": {},
        }
        assert job_result.unwrap() == expected_job_data

    def test_register_job__when_value_error_raised__returns_failure_result(self, service):
        service._dependencies.register_job_fn.side_effect = ValueError("Invalid user ID")
        job_result = service.register_job(user_id=0, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "Invalid user ID"

    def test_register_job__when_exception_raised__returns_failure_result(self, service):
        service._dependencies.register_job_fn.side_effect = Exception("Unexpected error")
        job_result = service.register_job(user_id=456, tags=["info_job"])
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while registering the job"

    def test_submit_job__calls_submit_job_fn_with_correct_parameters(self, service):
        service.submit_job(job_id=1, context="job", job_type="input")
        service._dependencies.submit_job_fn.assert_called_once_with(job_id=1, context="job", job_type="input")

    def test_submit_job__returns_success_result_with_response_data(self, service):
        expected_response = {"url": "http://example.com/pre-signed-url", "status": "submitted"}
        job_result = service.submit_job(job_id=1, context="job", job_type="input")
        assert is_successful(job_result)
        assert job_result.unwrap() == expected_response

    def test_submit_job__when_value_error_raised__returns_failure_result(self, service):
        service._dependencies.submit_job_fn.side_effect = ValueError("Invalid job ID")
        job_result = service.submit_job(job_id=0, context="job", job_type="input")
        assert not is_successful(job_result)
        assert job_result.failure() == "Invalid job ID"

    def test_submit_job__when_exception_raised__returns_failure_result(self, service):
        service._dependencies.submit_job_fn.side_effect = Exception("Unexpected error")
        job_result = service.submit_job(job_id=1, context="job", job_type="input")
        assert not is_successful(job_result)
        assert job_result.failure() == "An unexpected error occurred while submitting the job"
