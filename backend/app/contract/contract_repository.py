from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.contract.contract_models import (
    ContractReview,
    UploadBatch,
    UploadBatchExpanded,
    UploadBatchStatus,
    UploadFile,
    UploadStatus,
    WebSocketConnection,
)
from core.utils.datetime import utcnow


class ContractRepository:
    def __init__(
        self,
        upload_files_collection: AsyncIOMotorCollection,
        upload_batches_collection: AsyncIOMotorCollection,
        contract_reviews_collection: AsyncIOMotorCollection,
        contract_process_connections_collection: AsyncIOMotorCollection,
    ):
        self.upload_files_collection = upload_files_collection
        self.upload_batches_collection = upload_batches_collection
        self.contract_reviews_collection = contract_reviews_collection
        self.contract_process_connections_collection = (
            contract_process_connections_collection
        )

    #######################################################
    ############## UploadFile Operations ################
    #######################################################

    async def save_uploaded_file(self, uploaded_file: UploadFile):
        """
        Save metadata for an uploaded file in the uploaded_files collection.
        """
        await self.upload_files_collection.insert_one(
            UploadFile(
                **uploaded_file.model_dump(by_alias=True, exclude={"uploaded_by"}),
                uploaded_by=ObjectId(uploaded_file.uploaded_by),
            ).model_dump(by_alias=True)
        )

    async def update_uploaded_file_status(
        self, file_id: str, status: UploadStatus, reason: Optional[str] = None
    ):
        """
        Update the status and reason of an uploaded file.
        """
        update_fields = {"status": status, "updated_at": utcnow()}
        if reason:
            update_fields["reason"] = reason

        await self.upload_files_collection.update_one(
            {"_id": ObjectId(file_id)}, {"$set": update_fields}
        )

    async def get_uploaded_file_by_id(self, file_id: str) -> Optional[UploadFile]:
        """
        Retrieve an uploaded file by its file_id.
        """
        document = await self.upload_files_collection.find_one(
            {"_id": ObjectId(file_id)}
        )
        if document:
            return UploadFile(**document)
        return None

    async def get_user_uploaded_files(self, user_id: str) -> List[UploadFile]:
        """
        Retrieve all uploaded files for a user.
        """
        documents = await self.upload_files_collection.find(
            {"uploaded_by": ObjectId(user_id)}
        ).to_list(None)
        return [UploadFile(**doc) for doc in documents]

    async def get_user_reviews(
        self, user_id: str, page: Optional[int] = None, limit: Optional[int] = None
    ) -> List[ContractReview]:
        """
        Retrieve user reviews sorted by the latest (most recently updated) at the top.

        Args:
            user_id (str): The ID of the user.
            page (Optional[int]): The page number for pagination (1-indexed).
            limit (Optional[int]): The number of items per page.

        Returns:
            List[ContractReview]: A list of ContractReview objects.
        """
        query = {"reviewer_id": ObjectId(user_id)}

        sort_order = [("created_at", -1)]

        if page is not None and limit is not None:
            page = max(page, 1)
            limit = max(limit, 1)
            skip = (page - 1) * limit

            documents = (
                await self.contract_reviews_collection.find(query)
                .sort(sort_order)
                .skip(skip)
                .limit(limit)
                .to_list(limit)
            )
        else:
            documents = (
                await self.contract_reviews_collection.find(query)
                .sort(sort_order)
                .to_list(None)
            )

        return [ContractReview(**doc) for doc in documents]

    #######################################################
    ############## UploadBatch Operations #################
    #######################################################

    async def create_upload_batch(self, upload_batch: UploadBatch):
        res = await self.upload_batches_collection.insert_one(
            upload_batch.model_dump(by_alias=True)
        )
        if res.inserted_id:
            return upload_batch
        else:
            return None

    async def get_upload_batch_by_id(
        self, batch_id: str, user_id: str
    ) -> Optional[UploadBatch]:
        document = await self.upload_batches_collection.find_one(
            {"_id": ObjectId(batch_id), "uploaded_by": ObjectId(user_id)}
        )
        if document:
            return UploadBatch(**document)
        return None

    async def get_upload_batch_by_id_expanded(
        self, batch_id: str, user_id: str
    ) -> Optional[UploadBatchExpanded]:
        pipeline = [
            {"$match": {"_id": ObjectId(batch_id), "uploaded_by": ObjectId(user_id)}},
            {
                "$lookup": {
                    "from": "upload_files",  # collection name for files
                    "localField": "files",  # field in `upload_batches` referencing file IDs
                    "foreignField": "_id",  # field in `upload_files` that matches the IDs
                    "as": "expanded_files",  # resulting field to hold the joined data
                }
            },
        ]

        cursor = self.upload_batches_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)

        if result:
            batch_data = result[0]
            expanded_files = batch_data.pop("expanded_files", [])

            upload_files = [UploadFile(**file_doc) for file_doc in expanded_files]

            batch_data.pop("files", None)

            return UploadBatchExpanded(**batch_data, files=upload_files)

        return None

    async def update_batch_status(
        self, batch_id: str, status: UploadBatchStatus, user_id: str
    ):
        """
        Update the status of an upload batch.
        """
        await self.upload_batches_collection.update_one(
            {"_id": ObjectId(batch_id), "uploaded_by": ObjectId(user_id)},
            {"$set": {"status": status, "updated_at": utcnow()}},
        )

    #######################################################
    ############## ContractReview Operations ##############
    #######################################################

    async def save_contract_review(self, review: ContractReview):
        """
        Save a contract review in the contract_reviews collection.
        """
        await self.contract_reviews_collection.insert_one(
            review.model_dump(by_alias=True)
        )

    async def get_contract_review_by_id(
        self, review_id: str
    ) -> Optional[ContractReview]:
        """
        Retrieve a contract review by its ID.
        """
        document = await self.contract_reviews_collection.find_one(
            {"_id": ObjectId(review_id)}
        )
        if document:
            return ContractReview(**document)
        return None

    async def get_review_by_id(
        self, user_id: str, review_id: str
    ) -> ContractReview | None:
        """
        Retrieves a review by contract ID.
        """
        document = await self.contract_reviews_collection.find_one(
            {"_id": ObjectId(review_id), "reviewer_id": ObjectId(user_id)}
        )
        if document:
            return ContractReview(**document)
        return None

    async def get_user_uploaded_contracts(self, user_id: str) -> List[UploadFile]:
        """
        Retrieve all uploaded contracts for a user.
        """
        documents = await self.upload_files_collection.find(
            {"uploaded_by": ObjectId(user_id)}
        ).to_list(None)
        return [UploadFile(**doc) for doc in documents]

    async def get_uploaded_contract_by_id(
        self, user_id: str, file_id: str
    ) -> UploadFile | None:
        """
        Retrieve an uploaded contract by its ID.
        """
        document = await self.upload_files_collection.find_one(
            {"_id": ObjectId(file_id), "uploaded_by": ObjectId(user_id)}
        )
        if document:
            return UploadFile(**document)
        return None

    async def get_pending_tasks_for_user(self, user_id: str) -> List[UploadFile]:
        """
        Retrieve all pending tasks (QUEUED or PROCESSING files) for a given user.

        Args:
            user_id (str): The ID of the user.

        Returns:
            List[UploadFile]: A list of pending files for the user.
        """
        # Query the upload_files_collection for files with QUEUED or PROCESSING status
        documents = await self.upload_files_collection.find(
            {
                "uploaded_by": ObjectId(user_id),
                "status": {
                    "$in": [UploadStatus.QUEUED.value, UploadStatus.PROCESSING.value]
                },
            }
        ).to_list(None)

        # Convert documents to UploadFile models
        return [UploadFile(**doc) for doc in documents]

    async def get_reviews_by_ids(
        self, user_id: str, review_ids: List[str]
    ) -> List[ContractReview]:
        """
        Retrieve reviews by their IDs.
        """
        query = {"_id": {"$in": [ObjectId(id) for id in review_ids]}}
        documents = await self.contract_reviews_collection.find(query).to_list(None)
        return [ContractReview(**doc) for doc in documents]

    ###########################################################
    ##################### General Methods #####################
    ###########################################################

    async def delete_uploaded_file(self, file_id: str):
        """
        Delete an uploaded file and its associated reviews.
        """
        await self.upload_files_collection.delete_one({"_id": ObjectId(file_id)})
        await self.contract_reviews_collection.delete_many(
            {"contract_id": ObjectId(file_id)}
        )

    async def update_uploaded_file_processing_status(
        self, file_id: str, status: UploadStatus, reason: Optional[str] = None
    ):
        """
        Update the processing status of an uploaded file (e.g., PROCESSING, PROCESSED).
        """
        if reason:
            await self.upload_files_collection.update_one(
                {"_id": ObjectId(file_id)},
                {
                    "$set": {
                        "status": status,
                        "reason": reason,
                        "updated_at": utcnow(),
                    }
                },
            )
        else:
            await self.upload_files_collection.update_one(
                {"_id": ObjectId(file_id)},
                {"$set": {"status": status, "updated_at": utcnow()}},
            )

    ###########################################################
    ##################### Connections #########################
    ###########################################################
    async def save_connection(self, connection: WebSocketConnection):
        """
        Save a connection ID for a WebSocket client.
        """
        res = await self.contract_process_connections_collection.insert_one(
            connection.model_dump(by_alias=True)
        )
        if res.inserted_id:
            return str(res.inserted_id)

    async def delete_connection(self, connection_id: str):
        """
        Delete a connection ID for a WebSocket client.
        """
        res = await self.contract_process_connections_collection.delete_one(
            {"connection_id": ObjectId(connection_id)}
        )

        if res.deleted_count:
            return True

        return False

    async def get_active_connections(self, user_id: ObjectId):
        return await self.contract_process_connections_collection.find(
            {"user_id": ObjectId(user_id)}
        ).to_list(None)
