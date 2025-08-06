#!/usr/bin/env python3
"""
Script to set up test data for CLI testing.
Creates a sample job and run in the database.
"""

import datetime
from epistemix_api.repositories.database import get_database_manager, JobRecord, RunRecord
from epistemix_api.models.job import Job, JobStatus
from epistemix_api.models.run import Run, RunStatus

# Get database session
db_manager = get_database_manager('sqlite:///epistemix_jobs.db')
db_manager.create_tables()
session = db_manager.get_session()

try:
    
    # Create a test job
    job_record = JobRecord(
        id=999,
        user_id=456,
        tags=["test", "cli-demo"],
        status="CREATED",
        created_at=datetime.datetime.utcnow()
    )
    session.add(job_record)
    session.commit()
    print(f"Created test job with ID: {job_record.id}")
    
    # Create test runs for the job
    for i in range(3):
        run_record = RunRecord(
            id=5000 + i,
            job_id=999,
            user_id=456,
            status="DONE" if i < 2 else "RUNNING",
            pod_phase="Succeeded" if i < 2 else "Running",
            created_at=datetime.datetime.utcnow(),
            request={
                "jobId": 999,
                "workingDir": "/workspaces/fred_simulations",
                "size": "hot",
                "fredVersion": "latest",
                "population": {
                    "version": "US_2010.v5",
                    "locations": ["Allegheny_County_PA", "Jefferson_County_PA"][i % 2:i % 2 + 1]
                },
                "fredArgs": [
                    {"flag": "-p", "value": "main.fred"},
                    {"flag": "-days", "value": "30"}
                ],
                "fredFiles": [
                    f"/workspaces/fred_simulations/simulations/test_{i}.fred"
                ]
            },
            epx_client_version="1.2.2"
        )
        session.add(run_record)
    
    session.commit()
    print("Created 3 test runs for the job")
    
    print("\nTest data created successfully!")
    print("You can now test the CLI with:")
    print("  ./epistemix jobs info --job-id=999")
    
except Exception as e:
    session.rollback()
    print(f"Error creating test data: {e}")
    raise
finally:
    session.close()