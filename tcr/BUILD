poetry_requirements(
    name="tcr-reqs",
)

python_sources(
    name="tcr",
)

python_tests(
    name="tests",
    sources=["tests/test_*.py"],
    dependencies=[
        ":tcr",
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
    ],
)