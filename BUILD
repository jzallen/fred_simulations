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

docker_image(
    name="simulation-runner",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        "COPY epistemix_platform/epistemix-cli.pex /usr/local/bin/epistemix-cli",
        "RUN chmod +x /usr/local/bin/epistemix-cli",
        "COPY fred-framework/bin/FRED /usr/local/bin/FRED",
        "RUN chmod +x /usr/local/bin/FRED",
    ],
    dependencies=[
        ":fred-binary",
        "epistemix_platform:epistemix-cli",
    ],
)

docker_image(
    name="epistemix-api",
    image_tags=["latest"],
    instructions=[
        "FROM python:3.11-slim",
        # Install nginx and system dependencies
        "RUN apt-get update && apt-get install -y nginx curl && rm -rf /var/lib/apt/lists/*",
        # Create non-root user
        "RUN useradd -m -u 1000 apiuser",
        # Copy configurations
        "COPY epistemix_platform/configs/nginx.conf /etc/nginx/nginx.conf",
        "COPY epistemix_platform/configs/gunicorn.conf.py /app/configs/gunicorn.conf.py",
        # Copy startup script
        "COPY epistemix_platform/scripts/docker-entrypoint.sh /app/docker-entrypoint.sh",
        "RUN chmod +x /app/docker-entrypoint.sh",
        # Copy PEX binary
        "COPY epistemix_platform/app.pex /app/app.pex",
        "RUN chmod +x /app/app.pex",
        # Set environment - Add PEX bin to PATH so gunicorn is available
        "ENV PATH=/app/app.pex/bin:/app:$PATH",
        "ENV PEX_MODULE=gunicorn",
        "ENV FLASK_ENV=production",
        "ENV DATABASE_URL=sqlite:////app/epistemix_jobs.db",
        "ENV PYTHONUNBUFFERED=1",
        # Create necessary directories and set permissions
        "RUN mkdir -p /var/log/nginx /var/cache/nginx /var/run /tmp /var/lib/nginx",
        "RUN chown -R apiuser:apiuser /var/log/nginx /var/cache/nginx /var/run /tmp /app /var/lib/nginx",
        # Create writeable database directory
        "RUN mkdir -p /app && chown -R apiuser:apiuser /app",
        # Switch to non-root user
        "USER apiuser",
        "WORKDIR /app",
        # Expose port
        "EXPOSE 5555",
        # Health check
        "HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://localhost:5555/health || exit 1",
        # Start services
        "CMD [\"/app/docker-entrypoint.sh\"]",
    ],
    dependencies=[
        "epistemix_platform:app",
        "epistemix_platform:configs",
        "epistemix_platform:scripts",
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
