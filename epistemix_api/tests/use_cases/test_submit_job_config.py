from epistemix_api.models.upload_location import UploadLocation
from epistemix_api.use_cases.submit_job_config import submit_job_config


class TestSubmitJobConfigUseCase:
    
    def test_submit_job_config__returns_job_config_location(self):
        job_id = 1
        context = "job"
        job_type = "config"
        
        result = submit_job_config(job_id, context, job_type)
        
        assert isinstance(result, UploadLocation)
        assert result.url == "http://localhost:5001/pre-signed-url-job-config"
