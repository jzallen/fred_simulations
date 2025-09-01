# BUILD file for epistemix_api module

python_sources(
    name="cli",
    sources=["cli.py", "!tests/**/*.py"],
    dependencies=[
        "epistemix_api/controllers:lib",
        "epistemix_api/mappers:lib",
        "epistemix_api/models:lib",
        "epistemix_api/repositories:lib",
        "epistemix_api/use_cases:lib",
    ]
)

# Define the CLI as a PEX binary
pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_api.cli:cli",
    dependencies=[
        ":cli",
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

python_requirements(
    name="reqs",
)
