# BUILD file for epistemix_api use cases

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        ":lib",
        "epistemix_api/repositories:lib",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)