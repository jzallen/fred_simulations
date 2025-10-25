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

    S3 Key Structure (via JobS3Prefix):
        jobs/{job_id}/{yyyy}/{mm}/{dd}/{HHMMSS}/run_{run_id}_results.zip

    Example:
        jobs/123/2025/10/23/211500/run_4_results.zip
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
            ValueError: If job_id does not match s3_prefix.job_id
            ResultsStorageError: If S3 upload fails (with sanitized error message)
        """
        # CRITICAL INVARIANT: Ensure job_id matches prefix to avoid misplacing artifacts
        if s3_prefix.job_id != job_id:
            raise ValueError(
                f"s3_prefix.job_id ({s3_prefix.job_id}) does not match job_id ({job_id})"
            )

        object_key = s3_prefix.run_results_key(run_id)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=zip_content,
                ContentType="application/zip",
            )
            logger.info(
                f"Successfully uploaded results to S3: s3://{self.bucket_name}/{object_key}"
            )
        except ClientError as e:
            # CRITICAL SECURITY: Sanitize credentials before logging or raising
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"S3 upload failed: {sanitized_message}")  # noqa: TRY400
            raise ResultsStorageError(
                f"Failed to upload results to S3: {sanitized_message}", sanitized=True
            ) from e
        except Exception as e:
            # Catch-all for non-AWS errors (network, etc.)
            # These shouldn't contain credentials, but sanitize anyway for safety
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"Unexpected error during S3 upload: {sanitized_message}")  # noqa: TRY400
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
        # Extract bucket and object key from S3 URL
        try:
            bucket, object_key = self._extract_bucket_and_key(results_url)
        except ValueError as e:
            raise ValueError(f"Invalid S3 URL format: {e}") from e

        # Optional: Warn if bucket differs from repository configuration
        if bucket != self.bucket_name:
            logger.warning(
                f"Presigning URL for different bucket: {bucket} (repo bucket={self.bucket_name})"
            )

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": object_key,
                },
                ExpiresIn=expiration_seconds,
            )
            logger.info(
                f"Generated presigned download URL for {object_key}, expires in {expiration_seconds}s"
            )
        except ClientError as e:
            sanitized_message = self._sanitize_credentials(str(e))
            logger.error(f"Failed to generate presigned URL: {sanitized_message}")  # noqa: TRY400
            raise ResultsStorageError(
                f"Failed to generate download URL: {sanitized_message}", sanitized=True
            ) from e

        return UploadLocation(url=presigned_url)

    def _extract_key_from_url(self, s3_url: str) -> str:
        """
        Extract S3 object key from S3 URL (legacy helper).

        This method delegates to _extract_bucket_and_key for backward compatibility.

        Args:
            s3_url: S3 URL (various formats supported)

        Returns:
            S3 object key (e.g., "results/job_123/run_4.zip")

        Raises:
            ValueError: If URL format is not recognized
        """
        _, key = self._extract_bucket_and_key(s3_url)
        return key

    def _extract_bucket_and_key(self, s3_url: str) -> tuple[str, str]:
        """
        Extract bucket and key from common S3 URL formats.

        Supports:
        - s3://bucket/key
        - https://bucket.s3.amazonaws.com/key
        - https://bucket.s3.{region}.amazonaws.com/key
        - https://s3.amazonaws.com/bucket/key
        - https://s3.{region}.amazonaws.com/bucket/key

        Args:
            s3_url: S3 URL in any supported format

        Returns:
            Tuple of (bucket_name, object_key)

        Raises:
            ValueError: If URL format is not recognized

        Examples:
            >>> repo._extract_bucket_and_key("s3://my-bucket/path/to/file.zip")
            ('my-bucket', 'path/to/file.zip')
            >>> repo._extract_bucket_and_key("https://my-bucket.s3.amazonaws.com/path/to/file.zip")
            ('my-bucket', 'path/to/file.zip')
        """
        # s3://bucket/key
        if s3_url.startswith("s3://"):
            parts = s3_url[5:].split("/", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]
            raise ValueError(f"Unrecognized S3 URL format: {s3_url}")  # noqa: TRY003

        # Virtual-hosted-style:
        # - https://bucket.s3.amazonaws.com/key
        # - https://bucket.s3.us-east-1.amazonaws.com/key
        # - https://bucket.s3.dualstack.us-east-1.amazonaws.com/key
        # - https://bucket.s3-accelerate.amazonaws.com/key
        # - https://bucket.s3-accelerate.dualstack.amazonaws.com/key
        # - https://bucket.s3.us-gov-west-1.amazonaws.com/key
        # - https://bucket.s3.{region}.amazonaws.com.cn/key
        match = re.match(
            r"^https?://([^.]+)\.s3(?:[.-][a-z0-9-]+)*\.amazonaws\.com(?:\.cn)?/(.+?)(?:\?.*)?$",
            s3_url,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1), match.group(2)

        # Path-style:
        # - https://s3.amazonaws.com/bucket/key
        # - https://s3.us-east-1.amazonaws.com/bucket/key
        # - https://s3.dualstack.us-east-1.amazonaws.com/bucket/key
        # - https://s3.amazonaws.com.cn/bucket/key
        match = re.match(
            r"^https?://s3(?:[.-][a-z0-9-]+)*\.amazonaws\.com(?:\.cn)?/([^/]+)/(.+?)(?:\?.*)?$",
            s3_url,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1), match.group(2)

        raise ValueError(f"Unrecognized S3 URL format: {s3_url}")  # noqa: TRY003

    def _sanitize_credentials(self, error_message: str) -> str:
        """
        Remove AWS credentials from error messages.

        This is a CRITICAL SECURITY function that prevents AWS credentials
        from leaking into logs, monitoring systems, or user-facing error messages.

        Redacts:
        - AWS Access Key IDs (AKIA/ASIA/AGPA/AIDA/AROA/ANPA... formats)
        - AWS Secret Access Keys (base64-like strings 40+ chars)
        - AWS Signatures (base64-like strings 40+ chars)
        - Presigned URL query parameters (X-Amz-*)
        - Credentials in XML responses
        - Credentials in JSON responses

        Args:
            error_message: Raw error message that may contain credentials

        Returns:
            Sanitized error message with credentials replaced by placeholders
        """
        message = error_message

        # Pattern 1: AWS Access Key IDs (20 chars). Common prefixes: AKIA, ASIA, AGPA, AIDA, AROA, ANPA
        # Example: AKIAIOSFODNN7EXAMPLE -> [REDACTED_KEY]
        # Example: ASIAIOSFODNN7EXAMPLE -> [REDACTED_KEY]
        message = re.sub(
            r"(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[A-Z0-9]{16}", "[REDACTED_KEY]", message
        )

        # Pattern 2: AWS Secrets and signatures (40+ char base64-like strings)
        # Example: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY -> [REDACTED]
        message = re.sub(r"[A-Za-z0-9+/=]{40,}", "[REDACTED]", message)

        # Pattern 2b: Presign query params (avoid leaking in messages)
        # Redacts X-Amz-Credential, X-Amz-Signature, X-Amz-Security-Token, etc.
        message = re.sub(
            r"(X-Amz-(?:Credential|Signature|Security-Token|SignedHeaders|Algorithm|Expires))=[^&\s]+",
            r"\1=[REDACTED]",
            message,
            flags=re.IGNORECASE,
        )

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

        message = re.sub(
            r"<Signature>[^<]+</Signature>", "<Signature>[REDACTED]</Signature>", message
        )

        # Pattern 4: JSON credential fields
        # Example: "AWSAccessKeyId": "AKIA..."
        message = re.sub(
            r'"AWSAccessKeyId":\s*"[^"]+"', '"AWSAccessKeyId": "[REDACTED_KEY]"', message
        )

        message = re.sub(
            r'"SecretAccessKey":\s*"[^"]+"', '"SecretAccessKey": "[REDACTED]"', message
        )

        message = re.sub(r'"Signature":\s*"[^"]+"', '"Signature": "[REDACTED]"', message)

        return message
