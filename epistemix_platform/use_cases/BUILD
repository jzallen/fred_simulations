# BUILD file for epistemix_platform use cases

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        "epistemix_platform/repositories:lib",
        "epistemix_platform/models:lib",
        "epistemix_platform/mappers:lib",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)