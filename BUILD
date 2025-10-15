files(
    name="fred-framework",
    sources=["fred-framework/**"],
)

run_shell_command(
    name="build-fred",
    command="make",
    execution_dependencies=[":fred-framework"],
    workdir="fred-framework",
)

files(
    name="fred-binary",
    sources=["./fred-framework/bin/FRED"],
)

files(
    name="simulation-scripts",
    sources=["epistemix_platform/scripts/run-simulation.sh"],
)

docker_image(
    name="simulation-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        # Copy epistemix-cli PEX binary
        "COPY epistemix_platform/epistemix-cli.pex /usr/local/bin/epistemix-cli",
        "RUN chmod +x /usr/local/bin/epistemix-cli",
        # Copy FRED binary
        "COPY fred-framework/bin/FRED /usr/local/bin/FRED",
        "RUN chmod +x /usr/local/bin/FRED",
        # Copy simulation runner entrypoint script
        "COPY epistemix_platform/scripts/run-simulation.sh /usr/local/bin/run-simulation.sh",
        "RUN chmod +x /usr/local/bin/run-simulation.sh",
        # Create workspace directory for job downloads
        "RUN mkdir -p /workspace",
        # Set environment variables
        "ENV PYTHONUNBUFFERED=1",
        # Set entrypoint to simulation runner script
        "ENTRYPOINT [\"/usr/local/bin/run-simulation.sh\"]",
        # Default command shows help
        "CMD [\"--help\"]",
    ],
    dependencies=[
        ":fred-binary",
        ":simulation-scripts",
        "epistemix_platform:epistemix-cli",
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
        "RUN pip install --no-cache-dir alembic==1.13.0 psycopg2-binary==2.9.9 sqlalchemy==2.0.41 boto3==1.40.1 pydantic==2.11.7 returns==0.25.0",
        # Create mount point directory
        "RUN mkdir -p /fred_simulations",
        # Copy migration entrypoint script
        "COPY epistemix_platform/scripts/migration-entrypoint.sh /entrypoint.sh",
        "RUN chmod +x /entrypoint.sh",
        # Set working directory to match mount point
        "WORKDIR /fred_simulations",
        # Default environment for local development
        "ENV DATABASE_URL=postgresql://epistemix_user:epistemix_password@postgres:5432/epistemix_db",
        "ENV PYTHONUNBUFFERED=1",
        # Use entrypoint script
        "ENTRYPOINT [\"/entrypoint.sh\"]",
        # Default command shows migration status
        "CMD [\"alembic\", \"current\"]",
    ],
    dependencies=[
        "epistemix_platform:scripts",
    ],
)
