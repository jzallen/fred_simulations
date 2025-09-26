poetry_requirements(
    name="epistemix-reqs",
    resolve="epistemix_platform_env",
)

pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_platform.cli:cli",
    dependencies=[
        "./src/epistemix_platform:lib",
        ":epistemix-reqs#click",
        ":epistemix-reqs#requests",
        ":epistemix-reqs#returns",
        ":epistemix-reqs#pydantic",
        ":epistemix-reqs#boto3",
        ":epistemix-reqs#botocore",
        ":epistemix-reqs#python-dotenv",
        ":epistemix-reqs#sqlalchemy",
    ],
)

python_tests(
    name="src-tests",
    sources=[
        "tests/**/test_*.py",
        "tests/test_*.py",
    ],
    dependencies=[
        "./src/epistemix_platform:lib",
        "./tests:test-utils",
        "//:root#freezegun",
        "//:root#pytest"
    ],
)

python_tests(
    name="infrastructure-tests",
    sources=[
        "infrastructure/tests/**/test_*.py",
    ],
    dependencies=[
        "./infrastructure/tests:test-utils",
        "./infrastructure:lib",
        "./infrastructure:infrastructure-reqs#sceptre",
        "./infrastructure:infrastructure-reqs#jsonschema",
        "//:root#pytest",
    ],
)

pex_binary(
    name="epistemix_platform_test_runner",
    # No entry_point specified - this creates a Python interpreter with all dependencies
    dependencies=[
        ":src-tests",  # This will transitively include all needed dependencies
    ],
    # Use "prefer" to check system paths first, allowing VS Code pytest plugin to be found
    inherit_path="prefer",
)
