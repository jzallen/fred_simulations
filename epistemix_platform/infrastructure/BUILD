poetry_requirements(
    name="infrastructure-reqs",
    resolve="infrastructure_env",
)

# Bundle all infrastructure resources and code
target(
    name="lib",
    dependencies=[
        "./config:config",
        "./hooks:hooks",
        "./templates:templates",
    ],
)