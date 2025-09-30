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

files(
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