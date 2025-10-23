"""
S3-based repository for simulation results storage.

This module implements server-side S3 uploads using direct boto3 operations
with IAM credentials. It provides credential sanitization to prevent AWS
secrets from leaking into logs or error messages.

SECURITY NOTE: This repository handles AWS credentials and MUST sanitize
all error messages before logging or raising exceptions.
"""

import logging
import re

import boto3
from botocore.exceptions import ClientError

from epistemix_platform.exceptions import ResultsStorageError
from epistemix_platform.models.job_s3_prefix import JobS3Prefix
from epistemix_platform.models.upload_location import UploadLocation


logger = logging.getLogger(__name__)


class S3ResultsRepository:
    """
    S3-based repository for server-side simulation results uploads.

    This repository uses direct boto3.put_object() operations with IAM credentials,
    NOT presigned URLs. This is the correct approach for server-side uploads where
    the application has direct access to AWS credentials via IAM roles.

    Security Features:
    - Sanitizes AWS credentials from error messages before logging
    - Removes access keys, secrets, and signatures from exceptions
    - Uses IAM role credentials (no hardcoded secrets)

    S3 Key Structure:
        results/job_{job_id}/run_{run_id}.zip

    Example:
        results/job_123/run_4.zip
    """

    def __init__(self, s3_client: boto3.client, bucket_name: str):
        """
        Initialize S3 results repository.

        Args:
            s3_client: Configured boto3 S3 client (with IAM credentials)
            bucket_name: S3 bucket name for results storage
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def upload_results(
        self, job_id: int, run_id: int, zip_content: bytes, s3_prefix: JobS3Prefix
    ) -> UploadLocation:
        """
        Upload simulation results ZIP to S3 using IAM credentials.

        This is a server-side operation that uses the executing environment's
        IAM credentials to perform direct S3 PUT operations.

        S3 Key Format: {s3_prefix.base_prefix}/run_{run_id}_results.zip
        Example: jobs/12/2025/10/23/211500/run_4_results.zip
        Content-Type: application/zip

        Args:
            job_id: Job identifier
            run_id: Run identifier
            zip_content: Binary ZIP file content
            s3_prefix: JobS3Prefix for consistent path generation

        Returns:
            UploadLocation with S3 HTTPS URL (not presigned, permanent URL)

        Raises:
            ResultsStorageError: If S3 upload fails (with sanitized error message)
        """
        object_key = s3_prefix.run_results_key(run_id)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=zip_content,
                ContentType="application/zip",
            )
            logger.info(f"Successfully uploaded results to S3: s3://{self.bucket_name}/{object_key}")
        except ClientError as e:
            # CRITICAL SECURITY: Sanitize credentials before logging or raising
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"S3 upload failed: {sanitized_message}")
            raise ResultsStorageError(
                f"Failed to upload results to S3: {sanitized_message}", sanitized=True
            ) from e
        except Exception as e:
            # Catch-all for non-AWS errors (network, etc.)
            # These shouldn't contain credentials, but sanitize anyway for safety
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"Unexpected error during S3 upload: {sanitized_message}")
            raise ResultsStorageError(
                f"Unexpected error uploading to S3: {sanitized_message}", sanitized=True
            ) from e

        # Generate S3 HTTPS URL (permanent URL, not presigned)
        results_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"

        return UploadLocation(url=results_url)

    def get_download_url(self, results_url: str, expiration_seconds: int = 3600) -> UploadLocation:
        """
        Generate presigned GET URL for downloading results.

        This method creates a time-limited presigned URL that allows downloading
        the results ZIP file without requiring AWS credentials.

        Args:
            results_url: S3 URL of the results file
            expiration_seconds: URL validity period in seconds (default 1 hour)

        Returns:
            UploadLocation with presigned download URL

        Raises:
            ValueError: If results_url format is invalid
            ResultsStorageError: If presigned URL generation fails
        """
        # Extract object key from S3 URL
        try:
            object_key = self._extract_key_from_url(results_url)
        except ValueError as e:
            raise ValueError(f"Invalid S3 URL format: {e}") from e

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expiration_seconds,
            )
            logger.info(f"Generated presigned download URL for {object_key}, expires in {expiration_seconds}s")
        except ClientError as e:
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"Failed to generate presigned URL: {sanitized_message}")
            raise ResultsStorageError(
                f"Failed to generate download URL: {sanitized_message}", sanitized=True
            ) from e

        return UploadLocation(url=presigned_url)

    def _generate_results_key(self, job_id: int, run_id: int) -> str:
        """
        Generate S3 object key for results ZIP.

        Format: results/job_{job_id}/run_{run_id}.zip

        Args:
            job_id: Job identifier
            run_id: Run identifier

        Returns:
            S3 object key
        """
        return f"results/job_{job_id}/run_{run_id}.zip"

    def _extract_key_from_url(self, s3_url: str) -> str:
        """
        Extract S3 object key from S3 URL.

        Supports formats:
        - https://bucket.s3.amazonaws.com/results/job_123/run_4.zip
        - https://bucket.s3.us-east-1.amazonaws.com/results/job_123/run_4.zip
        - s3://bucket/results/job_123/run_4.zip

        Args:
            s3_url: S3 URL (various formats supported)

        Returns:
            S3 object key (e.g., "results/job_123/run_4.zip")

        Raises:
            ValueError: If URL format is not recognized
        """
        # Handle s3:// format
        if s3_url.startswith("s3://"):
            parts = s3_url[5:].split("/", 1)
            if len(parts) == 2:
                return parts[1]  # Return everything after bucket name

        # Handle https:// format with s3.amazonaws.com
        if "s3.amazonaws.com/" in s3_url:
            return s3_url.split("s3.amazonaws.com/")[1].split("?")[0]  # Remove query params if present

        # Handle regional https:// format with s3.{region}.amazonaws.com
        if ".s3." in s3_url and ".amazonaws.com/" in s3_url:
            return s3_url.split(".amazonaws.com/")[1].split("?")[0]

        raise ValueError(f"Unrecognized S3 URL format: {s3_url}")

    def _sanitize_credentials(self, error_message: str) -> str:
        """
        Remove AWS credentials from error messages.

        This is a CRITICAL SECURITY function that prevents AWS credentials
        from leaking into logs, monitoring systems, or user-facing error messages.

        Redacts:
        - AWS Access Key IDs (AKIA... format)
        - AWS Secret Access Keys (base64-like strings 40+ chars)
        - AWS Signatures (base64-like strings 40+ chars)
        - Credentials in XML responses
        - Credentials in JSON responses

        Args:
            error_message: Raw error message that may contain credentials

        Returns:
            Sanitized error message with credentials replaced by placeholders
        """
        message = error_message

        # Pattern 1: AWS Access Key IDs (AKIA followed by 16 alphanumeric chars)
        # Example: AKIAIOSFODNN7EXAMPLE -> [REDACTED_KEY]
        message = re.sub(r"AKIA[A-Z0-9]{16}", "[REDACTED_KEY]", message)

        # Pattern 2: AWS Secrets and signatures (40+ char base64-like strings)
        # Example: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY -> [REDACTED]
        message = re.sub(r"[A-Za-z0-9+/=]{40,}", "[REDACTED]", message)

        # Pattern 3: XML credential fields
        # Example: <AWSAccessKeyId>AKIA...</AWSAccessKeyId>
        message = re.sub(
            r"<AWSAccessKeyId>[^<]+</AWSAccessKeyId>",
            "<AWSAccessKeyId>[REDACTED_KEY]</AWSAccessKeyId>",
            message,
        )

        message = re.sub(
            r"<SecretAccessKey>[^<]+</SecretAccessKey>",
            "<SecretAccessKey>[REDACTED]</SecretAccessKey>",
            message,
        )

        message = re.sub(r"<Signature>[^<]+</Signature>", "<Signature>[REDACTED]</Signature>", message)

        # Pattern 4: JSON credential fields
        # Example: "AWSAccessKeyId": "AKIA..."
        message = re.sub(r'"AWSAccessKeyId":\s*"[^"]+"', '"AWSAccessKeyId": "[REDACTED_KEY]"', message)

        message = re.sub(r'"SecretAccessKey":\s*"[^"]+"', '"SecretAccessKey": "[REDACTED]"', message)

        message = re.sub(r'"Signature":\s*"[^"]+"', '"Signature": "[REDACTED]"', message)

        return message
