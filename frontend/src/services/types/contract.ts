export enum ContractType {
  SERVICE_LEVEL_AGREEMENT = "SERVICE_LEVEL_AGREEMENT",
  MASTER_SERVICE_AGREEMENT = "MASTER_SERVICE_AGREEMENT",
  NON_DISCLOSURE_AGREEMENT = "NON_DISCLOSURE_AGREEMENT",
  SIMPLE_AGREEMENT_FOR_FUTURE_EQUITY = "SIMPLE_AGREEMENT_FOR_FUTURE_EQUITY",
  OTHER = "OTHER",
}

export enum UploadStatus {
  UPLOADED = "UPLOADED", // File successfully uploaded to S3
  QUEUED = "QUEUED", // File is in the SQS queue awaiting processing
  PROCESSING = "PROCESSING", // File is being processed
  PROCESSED = "PROCESSED", // File processing is complete
  FAILED = "FAILED", // File upload or processing failed
  RETRYING = "RETRYING", // File processing is being retried after failure
  CANCELLED = "CANCELLED", // File processing was intentionally cancelled
}

export enum UploadBatchStatus {
  PROCESSING = "PROCESSING", // Batch is being processed
  FINISHED = "FINISHED", // Batch processing is complete
}

export interface Clause {
  key: string; // The key of the clause, e.g., "1.1" or "2.3.4"
  content: string;
}

export interface UploadFile {
  _id: string; // MongoDB ObjectId as a string
  batch_id: string; // MongoDB ObjectId as a string
  uploaded_by: string; // MongoDB ObjectId as a string
  file_name: string;
  status: UploadStatus;
  s3_key?: string | null;
  reason?: string | null;
  created_at: Date;
  updated_at: Date;
}

export interface ContractReview {
  _id: string; // MongoDB ObjectId as a string
  batch_id: string; // MongoDB ObjectId as a string
  contract_id: string; // MongoDB ObjectId as a string
  reviewer_id: string; // MongoDB ObjectId as a string
  file_name: string;
  clauses: Clause[];
  marked_html: string;
  contract_type: ContractType;
  pages: number;
  properties: Record<string, any>; // Key-value pairs for properties like Duration, Parties, etc.
  created_at: Date;
  updated_at: Date;
}


export interface UploadBatchExpanded {
  _id: string; // MongoDB ObjectId as a string
  uploaded_by: string; // MongoDB ObjectId as a string
  status: UploadBatchStatus;
  files: UploadFile[];
  created_at: Date;
  updated_at: Date;
}

export interface WebSocketConnection {
  _id: string; // MongoDB ObjectId as a string
  user_id: string; // MongoDB ObjectId as a string
  connection_id: string; // Unique WebSocket connection ID
  created_at: Date;
  updated_at: Date;
  active: boolean; // Whether the connection is active
}

export interface ContractExplainClauseRequest {
  clause: string;
}

export interface FilesUploadResponse {
  files: UploadFile[];
}
