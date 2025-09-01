# BUILD file for epistemix_api use cases

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        "epistemix_api/repositories:lib",
        "epistemix_api/models:lib",
        "epistemix_api/mappers:lib",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)