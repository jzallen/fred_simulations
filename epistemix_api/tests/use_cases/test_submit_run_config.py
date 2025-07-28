from epistemix_api.models.run import RunConfigLocation
from epistemix_api.use_cases import submit_run_config


class TestSubmitRunConfigUseCase:
    
    def test_submit_job_config__returns_job_config_location(self):
        job_id = 1
        run_id = 1
        context = "run"
        job_type = "config"
        
        result = submit_run_config(job_id, run_id, context, job_type)
        
        assert isinstance(result, RunConfigLocation)
        assert result.url == "http://localhost:5001/pre-signed-url-run-config"
