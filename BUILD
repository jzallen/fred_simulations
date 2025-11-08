files(
    name="fred-framework",
    sources=["fred-framework/**"],
)

run_shell_command(
    name="build-fred",
    command="make",
    execution_dependencies=[":fred-framework"],
    workdir="fred-framework",
    # Output files are captured by fred-binary and fred-data targets
)

files(
    name="fred-binary",
    sources=["./fred-framework/bin/FRED"],
)

files(
    name="fred-data",
    sources=["fred-framework/data/**"],
)

docker_image(
    name="simulation-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        # Install OpenMP runtime library for multi-threaded FRED execution
        "RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*",
        # Copy epistemix-cli PEX binary
        "COPY epistemix_platform/epistemix-cli.pex /usr/local/bin/epistemix-cli",
        "RUN chmod +x /usr/local/bin/epistemix-cli",
        # Copy simulation-runner Python CLI
        "COPY simulation_runner/simulation-runner-cli.pex /usr/local/bin/simulation-runner",
        "RUN chmod +x /usr/local/bin/simulation-runner",
        # Copy FRED binary and data (built by build-fred target)
        "COPY fred-framework/bin/FRED /usr/local/bin/FRED",
        "RUN chmod +x /usr/local/bin/FRED",
        "COPY fred-framework/data /fred-framework/data",
        # Create workspace directory for job downloads
        "RUN mkdir -p /workspace",
        # Set environment variables
        "ENV PYTHONUNBUFFERED=1",
        "ENV FRED_HOME=/fred-framework",
        # Configure OpenMP to use 4 threads (matches NCPU=4 in Makefile)
        # Can be overridden at runtime via container environment variables
        "ENV OMP_NUM_THREADS=4",
        # Use Python CLI as entrypoint
        "ENTRYPOINT [\"/usr/local/bin/simulation-runner\"]",
        # Default command shows help
        "CMD [\"--help\"]",
    ],
    dependencies=[
        ":fred-binary",
        ":fred-data",
        "epistemix_platform:epistemix-cli",
        "simulation_runner:simulation-runner-cli",
    ],
)

docker_image(
    name="epistemix-api",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        "COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter",
        "RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*",
        # Create non-root user
        "RUN useradd -m -u 1000 apiuser",
        "COPY epistemix_platform/configs/gunicorn.conf.py /app/configs/gunicorn.conf.py",
        "COPY epistemix_platform/app.pex /app/app.pex",
        "RUN chmod +x /app/app.pex",
        "ENV PATH=/app/app.pex/bin:/app:$PATH",
        "ENV FLASK_ENV=production",
        "ENV DATABASE_URL=sqlite:////app/epistemix_jobs.db",
        "ENV PYTHONUNBUFFERED=1",
        "ENV AWS_LAMBDA_EXEC_WRAPPER=/opt/extensions/lambda-adapter",
        "ENV PORT=8080",
        "RUN mkdir -p /app && chown -R apiuser:apiuser /app",
        "USER apiuser",
        "WORKDIR /app",
        "EXPOSE 8080",
        "HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://localhost:8080/health || exit 1",
        # Start gunicorn directly (Lambda Web Adapter handles the rest)
        "CMD [\"sh\", \"-c\", \"PEX_MODULE=gunicorn /app/app.pex -c /app/configs/gunicorn.conf.py epistemix_platform.wsgi:application\"]",
    ],
    dependencies=[
        "epistemix_platform:app",
        "epistemix_platform:configs",
    ],
)

docker_image(
    name="migration-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        # Install PostgreSQL client and build dependencies
        "RUN apt-get update && apt-get install -y postgresql-client gcc python3-dev libpq-dev && rm -rf /var/lib/apt/lists/*",
        # Install Python dependencies for migrations and the application
        "RUN pip install --no-cache-dir alembic==1.13.0 psycopg2-binary==2.9.9 sqlalchemy==2.0.41 boto3==1.40.1 pydantic==2.11.7 returns==0.25.0 python-dotenv==1.0.1",
        # Create mount point directory
        "RUN mkdir -p /fred_simulations",
        # Set working directory to match mount point
        "WORKDIR /fred_simulations",
        # Copy migration entrypoint script
        "COPY epistemix_platform/scripts/migration-entrypoint.sh /usr/local/bin/migration-entrypoint.sh",
        "RUN chmod +x /usr/local/bin/migration-entrypoint.sh",
        # Default environment for local development
        "ENV PYTHONUNBUFFERED=1",
        "ENV ENVIRONMENT=dev",
        # Set entrypoint to migration script
        "ENTRYPOINT [\"/usr/local/bin/migration-entrypoint.sh\"]",
        # Default command shows help for alembic
        "CMD [\"alembic\", \"--help\"]",
    ],
    dependencies=[
        "epistemix_platform:scripts",
    ],
)
