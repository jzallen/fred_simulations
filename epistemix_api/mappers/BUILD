# BUILD file for epistemix_api mappers

python_sources(
    name="lib",
    sources=[
        "*.py",
        "!*_test.py",
        "!test_*.py",
    ],
    dependencies=[
        "epistemix_api/models:lib",
        "epistemix_api/repositories:lib",
        "//:root#sqlalchemy",
    ],
)