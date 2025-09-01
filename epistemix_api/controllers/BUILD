# BUILD file for epistemix_api controllers

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        "epistemix_api/mappers:lib",
        "epistemix_api/models:lib",
        "epistemix_api/repositories:lib",
        "epistemix_api/use_cases:lib",  
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)