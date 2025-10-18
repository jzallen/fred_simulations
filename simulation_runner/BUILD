# Pants BUILD file for simulation_runner component

python_sources(
    name="simulation_runner",
    sources=["src/**/*.py"],
)

pex_binary(
    name="simulation-runner-cli",
    entry_point="simulation_runner.cli:cli",
    dependencies=["./src/simulation_runner:lib"],
    execution_mode="venv",
)

python_test_utils(
    name="test_utils",
    sources=["tests/conftest.py"],
    dependencies=[
        "./src/simulation_runner:lib",
    ],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        "./src/simulation_runner:lib",
        ":test_utils",
    ],
)

files(
    name="scripts",
    sources=["scripts/**/*.sh"],
)

files(
    name="readme",
    sources=["README.md"],
)
