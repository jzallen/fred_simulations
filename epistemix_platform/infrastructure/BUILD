poetry_requirements(
    name="infrastructure-reqs",
    resolve="infrastructure_env",
)

# Shell scripts for validation tools
shell_sources(
    name="scripts",
    sources=["scripts/*.sh"],
)

# CloudFormation Guard rules (policy-as-code)
resources(
    name="guard_rules",
    sources=["guard_rules/**/*.guard", "guard_rules/**/README.md"],
)

# cfn-lint configuration
resources(
    name="cfnlint-config",
    sources=[".cfnlintrc.yaml"],
)

# Bundle all infrastructure resources and code
target(
    name="lib",
    dependencies=[
        "./config:config",
        "./templates:templates",
        ":scripts",
        ":guard_rules",
        ":cfnlint-config",
    ],
)