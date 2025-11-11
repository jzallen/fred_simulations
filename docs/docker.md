# Docker Containers

The project includes three Docker images for deployment:

## Simulation Runner Container

Runs FRED simulations with the simulation-runner CLI:

```bash
# Build the image
pants package //:simulation-runner

# Run simulation workflow
docker run \
  -e FRED_HOME=/fred-framework \
  -e EPISTEMIX_API_URL=http://host.docker.internal:5000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  simulation-runner:latest run --job-id 12

# Show help
docker run simulation-runner:latest --help

# Validate configs only
docker run \
  -e FRED_HOME=/fred-framework \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  simulation-runner:latest validate --job-id 12

# Use epistemix-cli directly in the container
docker run --rm --entrypoint epistemix-cli \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  simulation-runner:latest jobs list
```

## API Server Container

Runs the Flask-based Epistemix API:

```bash
# Build the image
pants package //:epistemix-api

# Run the API server
docker run -p 8080:8080 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  epistemix-api:latest
```

## Migration Runner Container

Runs Alembic database migrations:

```bash
# Build the image
pants package //:migration-runner

# Run migrations
docker run \
  -v $(pwd):/fred_simulations \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  migration-runner:latest alembic upgrade head

# Show migration history
docker run \
  -v $(pwd):/fred_simulations \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  migration-runner:latest alembic history
```
