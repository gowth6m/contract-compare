import json
from typing import List, Optional

import boto3
from bson import ObjectId
from fastapi import HTTPException
from fastapi import UploadFile as FastAPIUploadFile

from app.contract.contract_models import (
    ContractReview,
    ContractType,
    UploadBatch,
    UploadBatchExpanded,
    UploadBatchStatus,
    UploadFile,
    UploadStatus,
)
from app.contract.contract_processor import ContractProcessor
from app.contract.contract_repository import ContractRepository
from app.user.user_models import User
from core.aws.s3 import S3Client
from core.aws.sqs import SQSClient
from core.config import config
from core.exceptions.base import (
    InternalServerErrorException,
    NotFoundException,
    UnprocessableEntity,
)
from core.utils.datetime import utcnow


class ContractController:
    def __init__(
        self,
        contract_repo: ContractRepository,
        s3_client: S3Client,
        sqs_client: SQSClient,
    ):
        self.contract_repo = contract_repo
        self.s3_client = s3_client
        self.sqs_client = sqs_client

    async def upload_contracts(
        self,
        current_user: User,
        files: List[FastAPIUploadFile],
    ) -> UploadBatchExpanded:
        """
        Upload multiple contracts, store metadata in DB, and queue them for processing.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided.")

        upload_files = []
        batch_id = str(ObjectId())

        for file in files:
            if file.content_type != "application/pdf":
                raise UnprocessableEntity(detail="Only PDF files are supported.")

            file_id = str(ObjectId())
            s3_key = f"contracts/{current_user.id}/{file_id}-{file.filename}"

            try:
                file_content = await file.read()

                # Upload file to S3
                self.s3_client.upload_file(
                    file_name=file.filename,
                    object_key=s3_key,
                    file_content=file_content,
                )

                # Queue for processing in SQS
                self.sqs_client.send_message(
                    message_body="File uploaded",
                    message_attributes={
                        "user_id": {
                            "DataType": "String",
                            "StringValue": str(current_user.id),
                        },
                        "file_id": {"DataType": "String", "StringValue": file_id},
                        "file_name": {
                            "DataType": "String",
                            "StringValue": file.filename,
                        },
                        "batch_id": {
                            "DataType": "String",
                            "StringValue": batch_id,
                        },
                        "s3_key": {"DataType": "String", "StringValue": s3_key},
                    },
                )

                # Save metadata to DB
                uploaded_file = UploadFile(
                    id=file_id,
                    batch_id=batch_id,
                    uploaded_by=current_user.id,
                    file_name=file.filename,
                    status=UploadStatus.QUEUED,
                    s3_key=s3_key,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                await self.contract_repo.save_uploaded_file(uploaded_file)
                upload_files.append(uploaded_file)

            except Exception as e:
                print(f"Error uploading file {file.filename}: {str(e)}")

        if not upload_files:
            raise InternalServerErrorException(detail="Failed to upload files.")

        # Create a new batch for the uploaded files
        batch = UploadBatch(
            id=batch_id,
            uploaded_by=current_user.id,
            status=UploadBatchStatus.PROCESSING,
            files=[file.id for file in upload_files],
        )

        res = await self.contract_repo.create_upload_batch(batch)
        if not res:
            raise InternalServerErrorException(detail="Failed to create upload batch.")

        return UploadBatchExpanded(
            **batch.model_dump(by_alias=True, exclude={"files"}), files=upload_files
        )

    async def process_uploaded_files(self, event: dict):
        print(f"Received event: {event}")

        print(f"Processing {len(event['Records'])} records...")

        print("OPEN AI")

        for record in event["Records"]:
            file_id = None
            user_id = None
            s3_key = None

            try:
                message_attributes = record.get("messageAttributes", {})
                file_id = message_attributes["file_id"]["stringValue"]
                file_name = message_attributes["file_name"]["stringValue"]
                user_id = message_attributes["user_id"]["stringValue"]
                s3_key = message_attributes["s3_key"]["stringValue"]
                batch_id = message_attributes["batch_id"]["stringValue"]

                print(
                    f"Processing file_id={file_id}, user_id={user_id}, s3_key={s3_key}, batch_id={batch_id}"
                )

                # Update status to PROCESSING
                await self.contract_repo.update_uploaded_file_processing_status(
                    file_id, UploadStatus.PROCESSING
                )

                # Retrieve PDF from S3
                pdf_content = self.s3_client.download_file(s3_key)

                # Convert PDF to HTML and extract clauses
                html_content, num_pages = ContractProcessor.convert_pdf_to_html(
                    pdf_content
                )
                marked_html, clauses = ContractProcessor.mark_clauses(html_content)

                # Extract key properties
                properties = await ContractProcessor.extract_key_properties(clauses)

                # Save ContractReview to the database
                contract_review = ContractReview(
                    file_name=file_name,
                    batch_id=batch_id,
                    upload_file_id=ObjectId(file_id),
                    reviewer_id=ObjectId(user_id),
                    clauses=clauses,
                    marked_html=marked_html,
                    contract_type=properties.get("type", ContractType.OTHER),
                    properties=properties,
                    pages=num_pages,
                )
                await self.contract_repo.save_contract_review(contract_review)

                # Update status to PROCESSED
                await self.contract_repo.update_uploaded_file_processing_status(
                    file_id, UploadStatus.PROCESSED
                )

                # Check if all files in the batch are processed to update status for batch
                batch: UploadBatchExpanded = (
                    await self.contract_repo.get_upload_batch_by_id_expanded(batch_id)
                )
                if not batch:
                    print(f"Batch {batch_id} not found.")
                    continue

                # Check if all files are either PROCESSED or FAILED
                all_processed_or_failed = all(
                    file.status in {UploadStatus.PROCESSED, UploadStatus.FAILED}
                    for file in batch.files
                )

                if all_processed_or_failed:
                    print(
                        f"All files in batch {batch_id} are either processed or failed."
                    )
                    await self.contract_repo.update_batch_status(
                        batch_id, UploadBatchStatus.FINISHED
                    )
                else:
                    print(f"Batch {batch_id} still has files in progress.")

                # # TODO: using polling for now, but maybe WebSocket if I have time

                # # Trigger WebSocket notification
                # await self.notify_user_of_completion(user_id, file_id)

                # # Check if all tasks are processed and disconnect WebSocket
                # await self.check_and_disconnect_websocket(user_id)

            except Exception as e:
                print(f"Error processing file {file_id or 'unknown file'}: {str(e)}")
                if file_id:
                    await self.contract_repo.update_uploaded_file_processing_status(
                        file_id, UploadStatus.FAILED, reason=str(e)
                    )

    async def notify_user_of_completion(self, user_id: str, file_id: str):
        """
        Notify the user via WebSocket when a file has been processed.
        """
        # Get active WebSocket connections for the user
        connections = await self.contract_repo.get_active_connections(user_id=user_id)

        message = json.dumps(
            {
                "event": "FILE_PROCESSED",
                "file_id": file_id,
                "message": f"File {file_id} has been processed successfully.",
            }
        )

        # TODO: Move this to a separate dependency or service
        apigw_client = boto3.client(
            "apigatewaymanagementapi", endpoint_url=config.WEB_SOCKET_URL
        )

        # Send notifications to all active connections for the user
        for connection in connections:
            connection_id = connection.connection_id
            try:
                apigw_client.post_to_connection(
                    ConnectionId=connection_id, Data=message
                )
            except Exception as e:
                print(f"Failed to send notification to connection {connection_id}: {e}")
                await self.contract_repo.delete_connection(connection_id)

    async def check_and_disconnect_websocket(self, user_id: str):
        """
        Check if all tasks related to the user are processed, and disconnect WebSocket if no pending tasks.
        """
        # Fetch pending tasks for the user
        pending_tasks = await self.contract_repo.get_pending_tasks_for_user(user_id)

        if not pending_tasks:
            print(f"No pending tasks for user {user_id}. Disconnecting WebSocket.")

            # Get active WebSocket connections for the user
            connections = await self.contract_repo.get_active_connections(
                user_id=user_id
            )

            apigw_client = boto3.client(
                "apigatewaymanagementapi", endpoint_url=config.WEB_SOCKET_URL
            )

            # Close each active connection
            for connection in connections:
                try:
                    apigw_client.delete_connection(
                        ConnectionId=connection.connection_id
                    )
                    await self.contract_repo.delete_connection(connection.connection_id)
                except Exception as e:
                    print(
                        f"Error disconnecting WebSocket connection {connection.connection_id}: {e}"
                    )

    async def get_all_reviews(
        self,
        current_user: User,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """
        Retrieve all contracts uploaded by the current user.
        """
        return await self.contract_repo.get_user_reviews(
            user_id=current_user.id, page=page, limit=limit
        )

    async def get_review_by_id(self, current_user: User, review_id: str):
        """
        Retrieve a single review by its ID.
        """
        contract = await self.contract_repo.get_review_by_id(
            user_id=current_user.id, review_id=review_id
        )
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found.")
        return contract

    async def get_all_uploaded_contracts(self, current_user: User):
        """
        Retrieve all contracts uploaded by the current user.
        """
        return await self.contract_repo.get_user_uploaded_contracts(
            user_id=current_user.id
        )

    async def get_uploaded_contract_by_id(self, current_user: User, file_id: str):
        """
        Retrieve a single upload by its ID.
        """
        contract = await self.contract_repo.get_uploaded_contract_by_id(
            user_id=current_user.id, file_id=file_id
        )
        if not contract:
            raise NotFoundException(detail="Contract not found.")
        return contract

    async def compare_contracts(self, current_user: User, contract_ids: List[str]):
        """
        Compare multiple contracts.
        """
        contracts = await self.contract_repo.get_reviews_by_ids(
            user_id=current_user.id, review_ids=contract_ids
        )
        if not contracts:
            raise NotFoundException(detail="No contracts found for comparison.")

        # TODO: Improve comparison logic with embeddings

        return contracts

    async def get_expanded_batch_by_id(self, current_user: User, batch_id: str):
        """
        Retrieve a single upload batch by its ID.
        """
        batch = await self.contract_repo.get_upload_batch_by_id_expanded(
            batch_id=batch_id, user_id=current_user.id
        )
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found.")
        return batch

    async def test_extract_properties(self, current_user: User, review_id: str):
        """
        Test extracting key properties from a contract.
        """
        review = await self.contract_repo.get_review_by_id(
            user_id=current_user.id, review_id=review_id
        )
        if not review:
            raise NotFoundException(detail="Review not found.")

        properties = await ContractProcessor.extract_key_properties(review.marked_html)
        return properties
