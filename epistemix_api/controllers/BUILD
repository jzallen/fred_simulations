# BUILD file for epistemix_api controllers

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        ":lib",
        "epistemix_api/use_cases:lib",
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)