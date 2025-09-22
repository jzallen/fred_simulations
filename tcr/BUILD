poetry_requirements(
    name="tcr-reqs",
)

python_tests(
    name="tests",
    sources=["tests/test_*.py"],
    dependencies=[
        "./src/tcr:lib",
        "./tests:test_utils",
        ":tcr-reqs#watchdog",
        "//:root#freezegun",
        "//:root#pytest",
        "//:root#pytest-xdist",
        "//:root#pyyaml",
    ],
)

pex_binary(
    name="tcr-cli",
    entry_point="tcr.cli:main",
    dependencies=[
        "./src/tcr:lib",
        "//:root#pyyaml",
        ":tcr-reqs#watchdog",
        ":tcr-reqs#setproctitle",
    ],
)