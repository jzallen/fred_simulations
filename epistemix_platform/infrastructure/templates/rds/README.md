# RDS PostgreSQL Setup for Epistemix Platform

Simple RDS PostgreSQL instance for POC/development use.

## Quick Start

1. **Set the database password**:
   ```bash
   export EPISTEMIX_DB_PASSWORD="your-secure-password"
   ```

2. **Deploy the RDS instance**:
   ```bash
   cd epistemix_platform/infrastructure
   sceptre launch dev/rds-postgres
   ```

3. **Get the connection details**:
   ```bash
   sceptre list outputs dev/rds-postgres
   ```

4. **Set the DATABASE_URL for migrations**:
   ```bash
   # Get the endpoint from the outputs above
   export DATABASE_URL="postgresql://epistemixuser:${EPISTEMIX_DB_PASSWORD}@<endpoint>:5432/epistemixdb"
   ```

5. **Run migrations**:
   ```bash
   docker-compose run --rm -e DATABASE_URL migration-runner alembic upgrade head
   ```

## Configuration

The template creates:
- A db.t3.micro PostgreSQL 15 instance (free tier eligible)
- 20GB of gp2 storage
- Public accessibility for easy POC access
- 7-day backup retention
- Security group allowing access from specified IP range

## Security Note

This is configured for POC use with public accessibility. For production:
- Use private subnets
- Restrict security group access
- Enable encryption
- Use AWS Secrets Manager for passwords
- Enable deletion protection

## Cleanup

To delete the RDS instance:
```bash
sceptre delete dev/rds-postgres
```

Note: A final snapshot will be created before deletion.