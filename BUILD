poetry_requirements(
    name="root",
)

docker_image(
    name="simulation-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        "COPY epistemix_api/epistemix-cli.pex /usr/local/bin/epistemix-cli",
        "RUN chmod +x /usr/local/bin/epistemix-cli",
    ],
    dependencies=[
        "epistemix_api:epistemix-cli",
    ]
)