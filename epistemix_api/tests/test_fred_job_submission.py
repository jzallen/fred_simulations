import os
import sys
import unittest
from unittest.mock import patch

from pathlib import Path

from pact import Consumer, Provider
from pact.matchers import Like, EachLike

# Add the root directory to the Python path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.agent_info_job import info_job

os.environ["PACT_VERIFIER_LOG_LEVEL"] = "DEBUG"

EPISETEMIX_MOCK_HOST = "localhost"
EPISTEMIX_MOCK_PORT = 5000

S3_MOCK_HOST = "localhost"  # Changed to localhost since it's a mock
S3_MOCK_PORT = 5001

EPISTEMIX_API_FOLDER = Path(__file__).parent.parent
EPISTEMIX_PACTS_DIR = EPISTEMIX_API_FOLDER / "pacts"
EPISTEMIX_LOGS_DIR = EPISTEMIX_API_FOLDER / "logs"


# Define mock server for epistemix api
epistemix_pact = Consumer('Consumer').has_pact_with(
    Provider('Epistemix'),
    host_name=EPISETEMIX_MOCK_HOST,
    port=EPISTEMIX_MOCK_PORT,
    pact_dir=EPISTEMIX_PACTS_DIR,
    log_dir=EPISTEMIX_LOGS_DIR,
)

# Define mock server for S3 api
s3_pact = Consumer('Consumer').has_pact_with(
    Provider('S3'),
    host_name=S3_MOCK_HOST,
    port=S3_MOCK_PORT,
    pact_dir=EPISTEMIX_PACTS_DIR,
    log_dir=EPISTEMIX_LOGS_DIR,
)


class TestAgentInfoJob(unittest.TestCase):
    """
    Test class for the Agent Info Job.
    """

    def setUp(self):
        # Start the pact mock service before each test
        super().setUp()
        # self.mock_request = patch("requests.put").start()
        epistemix_pact.start_service()
        s3_pact.start_service()


        # Define job registration response
        (
            epistemix_pact
            .upon_receiving("a job registration request")
            .with_request(
                method="POST",
                path="/jobs/register",
                headers={
                    "Offline-Token": "Bearer fake-token",
                    "content-type": "application/json",
                    "fredcli-version": "0.4.0",
                    "user-agent": "epx_client_1.2.2"
                },
                body={
                    "tags": ["info_job"]
                }
            )
            .will_respond_with(
                status=200,
                body={
                    "id": 123,
                    "userId": 456,
                    "tags": ["info_job"],
                }
            )
        )

        # Defin job input submission response
        (
            epistemix_pact
            .upon_receiving("a job submission request")
            .with_request(
                method="POST",
                path="/jobs",
                headers={
                    "Offline-Token": "Bearer fake-token",
                    "content-type": "application/json",
                    "fredcli-version": "0.4.0",
                    "user-agent": "epx_client_1.2.2"
                },
                body={
                    "jobId": 123,
                    "context": "job",
                    "type": "input"
                }
            )
            .will_respond_with(
                status=200,
                body={
                    "url": f"http://{S3_MOCK_HOST}:{S3_MOCK_PORT}/pre-signed-url",
                }
            )
        )

        # Define job input upload response
        (   s3_pact
            .upon_receiving("a job input upload request")
            .with_request(
                method="PUT",
                path="/pre-signed-url"
            )
            .will_respond_with(
                status=200,
                body={}
            )
        )

        # Define job run submission response
        (
            epistemix_pact
            .upon_receiving("a run submission request").with_request(
                method="POST",
                path="/runs",
                headers={
                    "Content-Length": Like("475"),
                    "Content-Type": "application/json",
                    "Host": Like("localhost:5000"),
                    "User-Agent": Like("epx_client_1.2.2"),
                    "Accept-Encoding": Like("gzip, deflate"),
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                    "Offline-Token": Like("Bearer fake-token"),
                    "Fredcli-Version": Like("0.4.0"),
                    "Version": Like("HTTP/1.1")
                },
                body={
                    "runRequests": EachLike({
                        "jobId": Like(123),
                        "workingDir": Like("/workspaces/fred_simulations"),
                        "size": Like("hot"),
                        "fredVersion": Like("latest"),
                        "population": {
                            "version": Like("US_2010.v5"),
                            "locations": EachLike("Loving_County_TX")
                        },
                        "fredArgs": EachLike({
                            "flag": Like("-p"),
                            "value": Like("main.fred")
                        }),
                        "fredFiles": EachLike("/workspaces/fred_simulations/simulations/agent_info.fred")
                    })
                }
            )
            .will_respond_with(
                status=200,
                body={
                    "runResponses": [{
                        "runId": 978,
                        "jobId": 123,
                        "status": "Submitted",
                        "errors": None,
                        "runRequest": {
                            "jobId": Like(123),
                            "workingDir": Like("/workspaces/fred_simulations"),
                            "size": Like("hot"),
                            "fredVersion": Like("latest"),
                            "population": {
                                "version": Like("US_2010.v5"),
                                "locations": EachLike("Loving_County_TX")
                            },
                            "fredArgs": EachLike({
                                "flag": Like("-p"),
                                "value": Like("main.fred")
                            }),
                            "fredFiles": EachLike("/workspaces/fred_simulations/simulations/agent_info.fred")
                        }
                    }]
                }
            )
        )

        # Define job run config submission response
        (
            epistemix_pact
            .upon_receiving("a job submission request")
            .with_request(
                method="POST",
                path="/jobs",
                headers={
                    "Offline-Token": "Bearer fake-token",
                    "content-type": "application/json",
                    "fredcli-version": "0.4.0",
                    "user-agent": "epx_client_1.2.2"
                },
                body={
                    "jobId": 123,
                    "context": "run",
                    "type": "config",
                    "runId": 978
                }
            )
            .will_respond_with(
                status=200,
                body={
                    "url": f"http://{S3_MOCK_HOST}:{S3_MOCK_PORT}/pre-signed-url-run",
                }
            )
        )

        # Define job config submission response
        (
            epistemix_pact
            .upon_receiving("a job submission request")
            .with_request(
                method="POST",
                path="/jobs",
                headers={
                    "Offline-Token": "Bearer fake-token",
                    "content-type": "application/json",
                    "fredcli-version": "0.4.0",
                    "user-agent": "epx_client_1.2.2"
                },
                body={
                    "jobId": 123,
                    "context": "job",
                    "type": "config",
                }
            )
            .will_respond_with(
                status=200,
                body={
                    "url": f"http://{S3_MOCK_HOST}:{S3_MOCK_PORT}/pre-signed-url-job-config",
                }
            )
        )

        (
            epistemix_pact
            .upon_receiving("a request to get runs by job_id").with_request(
                method="GET",
                path="/runs",
                query="job_id=123",
                headers={
                    "Content-Type": "application/json",
                    "Host": Like("localhost:5000"),
                    "User-Agent": Like("epx_client_1.2.2"),
                    "Accept-Encoding": Like("gzip, deflate"),
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                    "Offline-Token": Like("Bearer fake-token"),
                    "Fredcli-Version": Like("0.4.0"),
                    "Version": Like("HTTP/1.1")
                }
            ).will_respond_with(
                status=200,
                body={
                    "runs": [
                        {
                            "id": 978,
                            "jobId": 123,
                            "userId": 555,
                            "createdTs": "2023-10-01T12:00:00Z",
                            "request": {
                                "jobId": 123,
                                "workingDir": "/workspaces/fred_simulations",
                                "size": "hot",
                                "fredVersion": "latest",
                                "population": {
                                    "version": "US_2010.v5",
                                    "locations": ["Loving_County_TX"]
                                },
                                "fredArgs": [{
                                    "flag": "-p",
                                    "value": "main.fred"
                                }],
                                "fredFiles": ["/workspaces/fred_simulations/simulations/agent_info.fred"]
                            },
                            "podPhase": "Running",
                            "containerStatus": None,
                            "status": "DONE",
                            "userDeleted": False,
                            "epxClientVersion": "1.2.2",
                        }
                    ]
                }
            )
        )

        # Define run config upload response
        (   s3_pact
            .upon_receiving("a run config upload request")
            .with_request(
                method="PUT",
                path="/pre-signed-url-run"
            )
            .will_respond_with(
                status=200,
                body={}
            )
        )

        # Define job config upload response
        (   s3_pact
            .upon_receiving("a job config upload request")
            .with_request(
                method="PUT",
                path="/pre-signed-url-job-config"
            )
            .will_respond_with(
                status=200,
                body={}
            )
        )
        

    def tearDown(self):
        # Stop the pact mock service after each test
        epistemix_pact.stop_service()
        s3_pact.stop_service()
        # self.mock_request.stop()
        super().tearDown()

    def test_job_is_registered(self):
        """
        Test that the job is registered correctly.
        """

        # Execute the FREDJob
        with epistemix_pact, s3_pact:
            
            try:
                info_job.execute(300)
            except Exception as e:
                self.fail(f"Job execution failed: {e}")

        self.assertEqual(str(info_job.status), 'DONE')



if __name__ == "__main__":
    unittest.main()
