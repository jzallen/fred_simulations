# BUILD file for epistemix_api module

python_sources(
    name="lib",
    sources=["**/*.py", "!tests/**/*.py"],
)

# Define the CLI as a PEX binary
pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_api.cli:cli",
    dependencies=[
        ":lib",  # Include all epistemix_api source files
        "epistemix_api/models:lib",
        "//:root#click",
        "//:root#requests",
        "//:root#returns",
        "//:root#pydantic",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#python-dotenv",
        "//:root#sqlalchemy",
    ],
)