from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.config import config


class SQSClient:
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self.client = boto3.client("sqs")

    def send_message(self, message_body: str, message_attributes: dict = None):
        """
        Send a message to the SQS queue.

        :param message_body: The main message body (string or JSON).
        :param message_attributes: Additional attributes to send with the message (optional).
        :return: The response from SQS.
        """
        try:
            response = self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes or {},
            )
            return response
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to send message to SQS: {e}")

    def receive_messages(self, max_number: int = 10, wait_time: int = 0):
        """
        Receive messages from the SQS queue.

        :param max_number: Maximum number of messages to retrieve (default 10).
        :param wait_time: Wait time in seconds for long polling (default 0).
        :return: A list of messages.
        """
        try:
            response = self.client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_number,
                WaitTimeSeconds=wait_time,
            )
            return response.get("Messages", [])
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to receive messages from SQS: {e}")

    def delete_message(self, receipt_handle: str):
        """
        Delete a message from the SQS queue.

        :param receipt_handle: The receipt handle of the message to delete.
        """
        try:
            self.client.delete_message(
                QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
            )
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to delete message from SQS: {e}")


@lru_cache()
def get_sqs_client(queue_url: str = config.SQS_QUEUES.UPLOADED_FILES) -> SQSClient:
    return SQSClient(queue_url=queue_url)
