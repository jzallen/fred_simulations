poetry_requirements(
    name="simulations-reqs",
    module_mapping={
        "pact-python": ["pact", "pact.matchers"],
    }
)

files(
    name="fred-files",
    sources=["**/*.fred"]
)

python_sources(
    name="simulations",
    sources=["**/*.py", "!tests/**/*.py"],
)

python_tests(
    name="tests",
    sources=["tests/**/test_*.py"],
    dependencies=[
        ":simulations",
        ":fred-files",
        "//:root#pytest",
        "//:root#pytest-xdist",
        ":simulations-reqs#pact-python",
        ":simulations-reqs#epx",
    ],
)