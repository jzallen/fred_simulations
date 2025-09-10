poetry_requirements(
    name="tcr-reqs",
)

python_sources(
    name="tcr",
)

pex_binary(
    name="tcr-cli",
    entry_point="tcr.tcr:main",
    dependencies=[
        ":tcr",
        ":tcr-reqs#watchdog",
        ":tcr-reqs#pyyaml", 
        ":tcr-reqs#gitpython",
    ],
)