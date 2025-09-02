poetry_requirements(
    name="root",
)

files(
    name="fred-framework",
    sources=["fred-framework/**"],
)

run_shell_command(
    name="build-fred",
    command="make",
    execution_dependencies=[":fred-framework"],
    workdir="fred-framework",
)

files(
    name="fred-binary",
    sources=["./fred-framework/bin/FRED"],
)

docker_image(
    name="simulation-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        "COPY epistemix_platform/epistemix-cli.pex /usr/local/bin/epistemix-cli",
        "RUN chmod +x /usr/local/bin/epistemix-cli",
        "COPY fred-framework/bin/FRED /usr/local/bin/FRED",
        "RUN chmod +x /usr/local/bin/FRED",
    ],
    dependencies=[
        ":fred-binary",
        "epistemix_platform:epistemix-cli",
    ],
)

python_sources(
    name="0",
)

shell_sources(
    name="1",
)

python_tests(
    name="tests0",
)
