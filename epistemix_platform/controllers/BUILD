# BUILD file for epistemix_platform controllers

python_sources(
    name="lib",
    sources=[
        "*.py",
    ],
    dependencies=[
        "epistemix_platform/mappers:lib",
        "epistemix_platform/models:lib",
        "epistemix_platform/repositories:lib",
        "epistemix_platform/use_cases:lib",  
        "//:root#boto3",
        "//:root#botocore",
        "//:root#sqlalchemy",
    ]
)