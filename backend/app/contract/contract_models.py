from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.shared.models.mongodb_models import CoreBaseModel, PyObjectId
from core.utils.datetime import utcnow


class ContractType(str, Enum):
    SERVICE_LEVEL_AGREEMENT = "SERVICE_LEVEL_AGREEMENT"
    MASTER_SERVICE_AGREEMENT = "MASTER_SERVICE_AGREEMENT"
    NON_DISCLOSURE_AGREEMENT = "NON_DISCLOSURE_AGREEMENT"
    SIMPLE_AGREEMENT_FOR_FUTURE_EQUITY = "SIMPLE_AGREEMENT_FOR_FUTURE_EQUITY"
    OTHER = "OTHER"


class UploadStatus(str, Enum):
    UPLOADED = "UPLOADED"  # File successfully uploaded to S3
    QUEUED = "QUEUED"  # File is in the SQS queue awaiting processing
    PROCESSING = "PROCESSING"  # File is being processed
    PROCESSED = "PROCESSED"  # File processing is complete
    FAILED = "FAILED"  # File upload or processing failed
    RETRYING = "RETRYING"  # File processing is being retried after failure
    CANCELLED = "CANCELLED"  # File processing was intentionally cancelled


class UploadBatchStatus(str, Enum):
    FINISHED = "FINISHED"
    PROCESSING = "PROCESSING"
    # TODO: Add more statuses for error handling with queues


#####################################################################
######## DATABASE MODEL #############################################
#####################################################################


class Clause(BaseModel):
    key: str  # The key of the clause e.g. "1.1" or "2.3.4"
    content: str


class UploadFile(CoreBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    batch_id: PyObjectId
    uploaded_by: PyObjectId
    file_name: str
    status: UploadStatus = UploadStatus.UPLOADED
    s3_key: Optional[str] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ContractReview(CoreBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    upload_file_id: PyObjectId
    batch_id: PyObjectId
    reviewer_id: PyObjectId
    file_name: str
    clauses: List[Clause]
    marked_html: str
    contract_type: ContractType = ContractType.OTHER
    pages: int = 0
    properties: dict = {}  # Duration, Parties, Discount, Indemnity, etc.
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class UploadBatch(CoreBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    uploaded_by: PyObjectId
    status: UploadBatchStatus = UploadBatchStatus.PROCESSING
    files: List[PyObjectId] = []
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class UploadBatchExpanded(UploadBatch):
    files: List[UploadFile] = []


class WebSocketConnection(CoreBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    connection_id: str  # Unique WebSocket connection ID
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    active: bool = True  # Whether the connection is active


class CompareContractsResponse(BaseModel):
    reviews: List[ContractReview]


#####################################################################
######## REQUEST MODELS #############################################
#####################################################################


class ContractExplainClauseRequest(BaseModel):
    clause: str


class CompareContractsRequest(BaseModel):
    ids: List[str]


#####################################################################
######## RESPONSE MODELS ############################################
#####################################################################


class FilesUploadResponse(BaseModel):
    files: List[UploadFile]
