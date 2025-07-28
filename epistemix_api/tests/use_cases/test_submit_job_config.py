from epistemix_api.models.job import JobConfigLocation
from epistemix_api.use_cases.submit_job_config import submit_job_config


class TestSubmitJobConfigUseCase:
    """Test cases for the submit job configuration use case."""
    
    def test_submit_job_config__returns_job_config_location(self):
        """Test that submit_job_config returns a JobConfigLocation."""
        job_id = 1
        context = "job"
        job_type = "input"
        
        result = submit_job_config(job_id, context, job_type)
        
        assert isinstance(result, JobConfigLocation)
        assert result.url == "http://localhost:5001/pre-signed-url-job-config"
