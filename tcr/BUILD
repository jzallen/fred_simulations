poetry_requirements(
    name="tcr-reqs",
    resolve="tcr_env",
)

poetry_requirements(
    name="test-reqs",
    source="tests/pyproject.toml",
    resolve="tcr_env",
)

python_tests(
    name="tests",
    sources=["tests/test_*.py"],
    resolve="tcr_env",
    dependencies=[
        "./src/tcr:lib",
        "./tests:test_utils",
        ":tcr-reqs#pyyaml",
        ":tcr-reqs#watchdog",
        ":test-reqs#freezegun",
        ":test-reqs#pytest",
        ":test-reqs#pytest-xdist",
    ],
)

pex_binary(
    name="tcr-cli",
    entry_point="tcr.cli:main",
    resolve="tcr_env",
    dependencies=[
        "./src/tcr:lib",
        ":tcr-reqs#pyyaml",
        ":tcr-reqs#watchdog",
        ":tcr-reqs#setproctitle",
    ],
)