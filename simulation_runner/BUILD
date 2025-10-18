# Pants BUILD file for simulation_runner component

python_requirements(
    name="reqs",
    source="pyproject.toml",
    resolve="simulation_runner_env",
)

python_sources(
    name="simulation_runner",
    sources=["src/**/*.py"],
    resolve="simulation_runner_env",
)

pex_binary(
    name="simulation-runner-cli",
    entry_point="simulation_runner.cli:cli",
    dependencies=[":simulation_runner"],
    resolve="simulation_runner_env",
    execution_mode="venv",
)

python_test_utils(
    name="test_utils",
    sources=["tests/conftest.py"],
    resolve="simulation_runner_env",
    dependencies=[
        ":simulation_runner",
    ],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    resolve="simulation_runner_env",
    dependencies=[
        ":simulation_runner",
        ":test_utils",
    ],
)

files(
    name="readme",
    sources=["README.md"],
)
