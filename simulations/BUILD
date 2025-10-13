poetry_requirements(
    name="simulations-reqs",
    resolve="simulations_env",
    module_mapping={
        "pact-python": ["pact", "pact.matchers"],
    }
)

poetry_requirements(
    name="test-reqs",
    source="tests/pyproject.toml",
    resolve="simulations_env",
)

resources(
    name="fred-files",
    sources=["**/*.fred"]
)

python_sources(
    name="simulations",
    sources=["**/*.py", "!tests/**/*.py"],
    resolve="simulations_env",
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    resolve="simulations_env",
    dependencies=[
        ":simulations",
        ":fred-files",
        ":test-reqs#pytest",
        ":test-reqs#pytest-xdist",
        ":simulations-reqs#pact-python",
        ":simulations-reqs#epx",
    ],
)

pex_binary(
    name="run-agent-info-job",
    entry_point="run_agent_info_job.py",
    dependencies=[
        ":fred-files",
        ":simulations-reqs#epx",
    ],
    resolve="simulations_env",
)