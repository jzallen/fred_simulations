# BUILD file for epistemix_api repositories

python_sources(
    name="lib",
    sources=[
        "s3_upload_location_repository.py",
        "!test_*.py",
    ],
    dependencies=[
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
        "epistemix_api/models:lib",
    ]
)