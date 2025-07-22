"""
Tests for the Job business model.
"""

import pytest
from datetime import datetime, timedelta
from epistemix_api.models.job import Job, JobStatus, JobTag


class TestJob:
    """Test cases for the Job domain model."""
    
    def test_job_creation_with_valid_data(self):
        """Test creating a job with valid data."""
        job = Job(id=123, user_id=456, tags=["info_job"])
        
        assert job.id == 123
        assert job.user_id == 456
        assert job.tags == ["info_job"]
        assert job.status == JobStatus.CREATED
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
    
    def test_job_creation_with_invalid_id(self):
        """Test that creating a job with invalid ID raises ValueError."""
        with pytest.raises(ValueError, match="Job ID must be positive"):
            Job(id=0, user_id=456)
        
        with pytest.raises(ValueError, match="Job ID must be positive"):
            Job(id=-1, user_id=456)
    
    def test_job_creation_with_invalid_user_id(self):
        """Test that creating a job with invalid user ID raises ValueError."""
        with pytest.raises(ValueError, match="User ID must be positive"):
            Job(id=123, user_id=0)
        
        with pytest.raises(ValueError, match="User ID must be positive"):
            Job(id=123, user_id=-1)
    
    def test_create_new_factory_method(self):
        """Test the create_new factory method creates unpersisted jobs."""
        job = Job.create_new(user_id=456, tags=["info_job"])
        
        assert job.id is None  # Should be unpersisted
        assert not job.is_persisted()
        assert job.user_id == 456
        assert job.tags == ["info_job"]
        assert job.status == JobStatus.CREATED

    def test_create_persisted_factory_method(self):
        """Test the create_persisted factory method creates persisted jobs."""
        job = Job.create_persisted(job_id=123, user_id=456, tags=["info_job"])
        
        assert job.id == 123
        assert job.is_persisted()
        assert job.user_id == 456
        assert job.tags == ["info_job"]
        assert job.status == JobStatus.CREATED

    def test_to_dict_unpersisted_job_raises_error(self):
        """Test that to_dict raises error for unpersisted jobs."""
        job = Job.create_new(user_id=456, tags=["info_job"])
        
        with pytest.raises(ValueError, match="Cannot convert unpersisted job to dict"):
            job.to_dict()
    
    def test_add_tag(self):
        """Test adding tags to a job."""
        job = Job(id=123, user_id=456)
        initial_updated_at = job.updated_at
        
        # Add a new tag
        job.add_tag("info_job")
        assert "info_job" in job.tags
        assert job.updated_at > initial_updated_at
        
        # Adding the same tag should not duplicate it
        job.add_tag("info_job")
        assert job.tags.count("info_job") == 1
    
    def test_remove_tag(self):
        """Test removing tags from a job."""
        job = Job(id=123, user_id=456, tags=["info_job", "test_job"])
        initial_updated_at = job.updated_at
        
        # Remove an existing tag
        job.remove_tag("info_job")
        assert "info_job" not in job.tags
        assert "test_job" in job.tags
        assert job.updated_at > initial_updated_at
        
        # Removing a non-existent tag should not raise an error
        job.remove_tag("non_existent_tag")
    
    def test_status_transitions(self):
        """Test valid status transitions."""
        job = Job(id=123, user_id=456)
        
        # Valid transition: CREATED -> SUBMITTED
        job.update_status(JobStatus.SUBMITTED)
        assert job.status == JobStatus.SUBMITTED
        
        # Valid transition: SUBMITTED -> PROCESSING
        job.update_status(JobStatus.PROCESSING)
        assert job.status == JobStatus.PROCESSING
        
        # Valid transition: PROCESSING -> COMPLETED
        job.update_status(JobStatus.COMPLETED)
        assert job.status == JobStatus.COMPLETED
    
    def test_invalid_status_transitions(self):
        """Test invalid status transitions."""
        job = Job(id=123, user_id=456)
        
        # Invalid transition: CREATED -> COMPLETED
        with pytest.raises(ValueError, match="Invalid status transition"):
            job.update_status(JobStatus.COMPLETED)
        
        # Invalid transition from terminal state
        job.update_status(JobStatus.SUBMITTED)
        job.update_status(JobStatus.PROCESSING)
        job.update_status(JobStatus.COMPLETED)
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            job.update_status(JobStatus.PROCESSING)
    
    def test_is_active(self):
        """Test the is_active method."""
        job = Job(id=123, user_id=456)
        
        # Non-terminal states should be active
        assert job.is_active()  # CREATED
        
        job.update_status(JobStatus.SUBMITTED)
        assert job.is_active()
        
        job.update_status(JobStatus.PROCESSING)
        assert job.is_active()
        
        # Terminal states should not be active
        job.update_status(JobStatus.COMPLETED)
        assert not job.is_active()
    
    def test_has_tag(self):
        """Test the has_tag method."""
        job = Job(id=123, user_id=456, tags=["info_job", "test_job"])
        
        assert job.has_tag("info_job")
        assert job.has_tag("test_job")
        assert not job.has_tag("non_existent_tag")
    
    def test_to_dict(self):
        """Test the to_dict method with persisted job."""
        job = Job.create_persisted(job_id=123, user_id=456, tags=["info_job"])
        job_dict = job.to_dict()
        
        assert job_dict["id"] == 123
        assert job_dict["userId"] == 456  # Note: camelCase for API compatibility
        assert job_dict["tags"] == ["info_job"]
        assert job_dict["status"] == JobStatus.CREATED.value
        assert "createdAt" in job_dict
        assert "updatedAt" in job_dict
    
    def test_equality_and_hash(self):
        """Test equality and hash methods for persisted and unpersisted jobs."""
        # Test persisted jobs - equality based on ID
        job1 = Job.create_persisted(job_id=123, user_id=456)
        job2 = Job.create_persisted(job_id=123, user_id=789)  # Different user_id but same job id
        job3 = Job.create_persisted(job_id=124, user_id=456)  # Different job id
        
        # Jobs with same ID should be equal
        assert job1 == job2
        assert hash(job1) == hash(job2)
        
        # Jobs with different ID should not be equal
        assert job1 != job3
        assert hash(job1) != hash(job3)
        
        # Test unpersisted jobs - equality based on object identity
        unpersisted1 = Job.create_new(user_id=456)
        unpersisted2 = Job.create_new(user_id=456)  # Same user but different object
        
        # Different unpersisted job objects should not be equal
        assert unpersisted1 != unpersisted2
        assert hash(unpersisted1) != hash(unpersisted2)
        
        # Same object should be equal to itself
        assert unpersisted1 == unpersisted1
        assert hash(unpersisted1) == hash(unpersisted1)
    
    def test_repr(self):
        """Test string representation for persisted and unpersisted jobs."""
        # Test persisted job
        persisted_job = Job.create_persisted(job_id=123, user_id=456, tags=["info_job"])
        repr_str = repr(persisted_job)
        
        assert "Job(" in repr_str
        assert "id=123" in repr_str
        assert "user_id=456" in repr_str
        assert "status=created" in repr_str
        
        # Test unpersisted job
        unpersisted_job = Job.create_new(user_id=789, tags=["test_job"])
        repr_str = repr(unpersisted_job)
        
        assert "Job(" in repr_str
        assert "id=unpersisted" in repr_str
        assert "user_id=789" in repr_str
        assert "status=created" in repr_str
