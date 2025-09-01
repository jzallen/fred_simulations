# BUILD file for epistemix_platform module

python_sources(
    name="cli",
    sources=["cli.py"],
    dependencies=[
        "epistemix_platform/controllers:lib",
        "epistemix_platform/mappers:lib",
        "epistemix_platform/models:lib",
        "epistemix_platform/repositories:lib",
        "epistemix_platform/use_cases:lib",
    ]
)

# Define the CLI as a PEX binary
pex_binary(
    name="epistemix-cli",
    entry_point="epistemix_platform.cli:cli",
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
