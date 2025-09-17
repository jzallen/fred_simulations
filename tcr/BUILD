poetry_requirements(
    name="tcr-reqs",
)

python_sources(
    name="tcr",
)

python_test_utils(
    name="test-utils",
    sources=["tests/conftest.py"],
)

python_tests(
    name="tests",
    sources=["tests/test_*.py"],
    dependencies=[
        ":tcr",
        ":test-utils",
        ":tcr-reqs#pytest",
        ":tcr-reqs#pytest-xdist",
        ":tcr-reqs#freezegun",
        ":tcr-reqs#watchdog",
        ":tcr-reqs#pyyaml",
    ],
)

pex_binary(
    name="tcr-cli",
    entry_point="tcr.tcr:main",
    dependencies=[
        ":tcr",
        ":tcr-reqs#watchdog",
        ":tcr-reqs#pyyaml",
        ":tcr-reqs#setproctitle",
    ],
)