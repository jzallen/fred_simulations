# BUILD file for epistemix_api repositories

python_sources(
    name="lib",
    sources=[
        "*.py"
    ],
    dependencies=[
        "epistemix_api/models:lib",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)