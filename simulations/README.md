# Simulations

This module contains FRED simulation configurations, job definitions, and contract tests for the Epistemix Platform API integration.

## Overview

The simulations module demonstrates how to:
- Define and execute FRED epidemiological simulations
- Integrate with the Epistemix Platform API using the `epx` client
- Implement consumer-driven contract testing with Pact

## Structure

```
simulations/
├── agent_info_demo/     # Example FRED simulation for agent demographics
│   ├── agent_info.fred  # FRED model configuration
│   └── agent_info_job.py # Job definition using epx client
├── pacts/               # Pact contract files (when persisted)
│   ├── epx-epistemix.json # Contract between epx client and Epistemix API
│   └── epx-s3.json        # Contract for S3 upload interactions
└── tests/               # Test suites
    └── pacts/           # Consumer-driven contract tests
        └── test_epx_provider_pact_for_agent_info_job.py # Pact tests for agent info job
```

## EPX Client and Pact Contract Testing

### About EPX

The `epx` client is a Python package for interacting with the Epistemix Platform API. It handles:
- Job registration and submission
- File uploads to S3
- Simulation execution and monitoring
- Results retrieval

### Consumer-Driven Contract Testing with Pact

This module uses [Pact](https://docs.pact.io/) for consumer-driven contract testing. The tests in `tests/pacts/` define the expected interactions between the `epx` client (consumer) and the Epistemix Platform API (provider).

#### How Pact Works

1. **Consumer tests** define expected API interactions using a mock provider
2. **Pact files** (JSON contracts) are generated containing these interaction specifications
3. **Provider verification** uses these contracts to ensure the API meets consumer expectations
4. **Contract sharing** via Pact Broker enables continuous integration between teams

### Pact File Generation

By default, Pact files are written to a temporary directory and cleaned up after test execution. This prevents unnecessary file changes during regular test runs.

#### Persisting Pact Files

To generate and persist Pact files to `simulations/pacts/`:

**Using Pants:**
```bash
# Generate pact files to simulations/pacts
pants test simulations:tests --test-extra-env-vars="['PACTS_OUTPUT_DIR=/workspaces/fred_simulations/simulations/pacts']"

# Or use a relative path from the test execution context
pants test simulations:tests --test-extra-env-vars="['PACTS_OUTPUT_DIR=simulations/pacts']"
```

**Using Poetry directly:**
```bash
cd simulations
export PACTS_OUTPUT_DIR=/workspaces/fred_simulations/simulations/pacts
poetry run python -m unittest tests.pacts.test_epx_provider_pact_for_agent_info_job
```

**Environment Variable:**
- `PACTS_OUTPUT_DIR`: Directory where Pact files should be written
- If not set, uses a temporary directory that is cleaned up after tests

### Relevance to Provider Development

The generated Pact JSON files are crucial for provider (Epistemix Platform API) development:

1. **Contract Verification**: Providers run these contracts against their implementation to ensure compatibility
2. **Backwards Compatibility**: Contracts help maintain compatibility when either consumer or provider changes
3. **API Documentation**: Contracts serve as living documentation of actual API usage
4. **Integration Testing**: Replaces brittle end-to-end tests with fast, reliable contract tests

#### Pact Broker Integration

In a production workflow, these contracts would typically be:
1. Published to a [Pact Broker](https://docs.pact.io/pact_broker) after successful consumer tests
2. Retrieved by the provider for verification during their CI/CD pipeline
3. Used to generate a compatibility matrix showing which versions can be deployed together

The Pact Broker enables:
- Automatic provider verification when contracts change
- "Can I Deploy?" checks before releasing services
- Webhook triggers for continuous integration
- Visualization of service dependencies

## Running Tests

### Unit Tests
```bash
# Using Pants (recommended)
pants test simulations:tests

# Using Poetry
cd simulations
poetry run python -m unittest discover tests
```

### Running Simulations

```python
from agent_info_demo.agent_info_job import info_job

# Execute the simulation
info_job.execute(timeout=300)
```

## Dependencies

- `pact-python`: Consumer-driven contract testing framework
- `epx`: Epistemix Platform API client
- Python 3.11+

## Development

When modifying consumer tests:
1. Update the test expectations in `tests/pacts/test_epx_provider_pact_for_agent_info_job.py`
2. Generate new Pact files using the `PACTS_OUTPUT_DIR` environment variable
3. Share updated contracts with the provider team (via Pact Broker or repository)
4. Ensure provider verification passes before deployment

## Best Practices

1. **Contract Tests First**: Write Pact tests before implementing consumer code
2. **Minimal Contracts**: Only specify fields your consumer actually uses
3. **Version Contracts**: Tag contracts with consumer version and branch
4. **Regular Verification**: Providers should verify contracts in CI/CD pipeline
5. **Breaking Changes**: Coordinate contract changes between consumer and provider teams