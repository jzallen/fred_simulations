"""
Tests for the Epistemix API Flask app to validate Pact contract compliance.
"""

# TODO: I don't know that the verify is intended to work this way. I think CLI is the
# preferred method. May need to delete this later.

# import json
# import pytest
# import sys
# import os
# import subprocess
# import time
# from pathlib import Path
# from pact import Verifier


# os.environ['PYTHONUNBUFFERED'] = "1"


# @pytest.fixture(scope="module")
# def server():
#     """Start a Flask server for Pact verification tests using run_server.py."""
#     # Get the path to run_server.py
#     server_script = Path(__file__).parent.parent / 'run_server.py'

#     # Start the server process with the correct PYTHONPATH
#     env = os.environ.copy()
#     env['FLASK_PORT'] = '5000'
#     env['FLASK_HOST'] = 'localhost'
#     env['FLASK_DEBUG'] = 'False'

#     # Add the workspace root to PYTHONPATH so epistemix_api can be imported
#     workspace_root = Path(__file__).parent.parent.parent
#     if 'PYTHONPATH' in env:
#         env['PYTHONPATH'] = f"{workspace_root}:{env['PYTHONPATH']}"
#     else:
#         env['PYTHONPATH'] = str(workspace_root)

#     server_process = subprocess.Popen(
#         [sys.executable, str(server_script)],
#         env=env,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         cwd=str(workspace_root)
#     )

#     # Give the server time to start
#     time.sleep(5)

#     # Check if the process is still running
#     if server_process.poll() is not None:
#         stdout, stderr = server_process.communicate()
#         pytest.fail(f"Server failed to start. STDOUT: {stdout.decode()}, STDERR: {stderr.decode()}")

#     yield

#     # Clean up - terminate the server process
#     try:
#         server_process.terminate()
#         server_process.wait(timeout=5)
#     except subprocess.TimeoutExpired:
#         server_process.kill()
#         server_process.wait()


# class TestPactCompliance:
#     """Test Pact contract compliance using ProviderVerifier."""

#     def test_pact_verification(self, server):
#         """Verify that the API complies with the Pact contract."""
#         # Absolute path to the pact JSON file
#         pact_path = str(Path(__file__).parent.parent / 'pacts' / 'epx-epistemix.json')

#         # URL where the API is running
#         provider_base_url = 'http://localhost:5000'

#         # Verify the contract exists
#         assert os.path.exists(pact_path), f"Pact file not found at {pact_path}"

#         # Create verifier instance with required parameters
#         verifier = Verifier(
#             provider='Epistemix',
#             provider_base_url=provider_base_url
#         )

#         # Run the verification - pass the pact file path directly as an argument
#         try:
#             result = verifier.verify_pacts(
#                 pact_path,
#                 verbose=True,
#                 enable_pending=True,
#             )

#             # The verify_pacts method returns 0 for success, non-zero for failure
#             assert result == 0, f"Pact verification failed with exit code: {result}"

#         except Exception as e:
#             pytest.fail(f"Pact verification failed with exception: {str(e)}")


# class TestPactFileStructure:
#     """Test the structure and content of the Pact file itself."""

#     def test_pact_file_exists(self):
#         """Test that the Pact file exists and is readable."""
#         pact_path = Path(__file__).parent.parent / 'pacts' / 'epx-epistemix.json'
#         assert pact_path.exists(), "Pact file does not exist"

#         # Verify it's valid JSON
#         with open(pact_path, 'r') as f:
#             pact_data = json.load(f)

#         # Verify basic structure
#         assert 'consumer' in pact_data
#         assert 'provider' in pact_data
#         assert 'interactions' in pact_data
#         assert pact_data['consumer']['name'] == 'epx'
#         assert pact_data['provider']['name'] == 'Epistemix'

#     def test_pact_interactions_structure(self):
#         """Test that all interactions have the required structure."""
#         pact_path = Path(__file__).parent.parent / 'pacts' / 'epx-epistemix.json'

#         with open(pact_path, 'r') as f:
#             pact_data = json.load(f)

#         interactions = pact_data['interactions']
#         assert len(interactions) > 0, "No interactions found in Pact file"

#         for interaction in interactions:
#             # Verify required fields
#             assert 'description' in interaction
#             assert 'request' in interaction
#             assert 'response' in interaction

#             # Verify request structure
#             request = interaction['request']
#             assert 'method' in request
#             assert 'path' in request

#             # Verify response structure
#             response = interaction['response']
#             assert 'status' in response
