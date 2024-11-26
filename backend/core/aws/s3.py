from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.config import config


class S3Client:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = boto3.client("s3")

    def upload_file(self, file_name: str, object_key: str, file_content: bytes):
        """
        Upload a file to S3.

        :param file_name: Original file name (optional for logging/debugging).
        :param object_key: S3 object key (file path within the bucket).
        :param file_content: File content as bytes.
        :return: S3 response.
        """
        try:
            response = self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType="application/pdf",
            )
            return response
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to upload file '{file_name}' to S3: {e}")

    def download_file(self, object_key: str):
        """
        Download a file from S3.

        :param object_key: S3 object key (file path within the bucket).
        :return: The file content as bytes.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            return response["Body"].read()
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to download file from S3: {e}")

    def generate_presigned_url(self, object_key: str, expiration: int = 3600):
        """
        Generate a presigned URL for an S3 object.

        :param object_key: S3 object key (file path within the bucket).
        :param expiration: URL expiration time in seconds (default 1 hour).
        :return: The presigned URL.
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expiration,
            )
            return url
        except (BotoCoreError, ClientError) as e:
            raise Exception(
                f"Failed to generate presigned URL for S3 object '{object_key}': {e}"
            )


@lru_cache()
def get_s3_client(bucket_name: str = config.S3_BUCKETS.UPLOADED_FILES) -> S3Client:
    return S3Client(bucket_name=bucket_name)
