from enum import Enum
from typing import ClassVar

import convertapi
import openai
from pydantic_settings import BaseSettings

from core.aws.secrets_manager import (
    get_base_secrets,
    get_s3_secrets,
    get_sqs_secrets,
    get_websocket_secrets,
)


class EnvironmentType(str, Enum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"
    LOCAL = "local"
    TEST = "test"


class MongoDBCollections(BaseSettings):
    USERS: str = "users"
    UPLOAD_FILES: str = "upload_files"
    UPLOAD_BATCHES: str = "upload_batches"
    CONTRACT_REVIEWS: str = "contract_reviews"
    ANALYTICS: str = "analytics"
    CONTRACT_PROCESS_CONNECTIONS: str = "contract_process_connections"


class MongoDBDatabase(BaseSettings):
    CORE: str = "contract_compare"


class S3Buckets(BaseSettings):
    UPLOADED_FILES: str = get_s3_secrets().UPLOADED_FILES


class SQSQueues(BaseSettings):
    UPLOADED_FILES: str = get_sqs_secrets().UPLOADED_FILES


class BaseConfig(BaseSettings):
    class Config:
        case_sensitive = True


class Config(BaseConfig):
    DEBUG: int = 0
    DEFAULT_LOCALE: str = "en_GB"
    RELEASE_VERSION: str = "1.0.0"
    META_APP_NAME: str = "Contract Compare"
    META_APP_DESCRIPTION: str = "API Service for Contract Compare"
    ENVIRONMENT: str = EnvironmentType.LOCAL

    # Auth
    JWT_SECRET_KEY: str = get_base_secrets().JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Database
    MONGODB_URL: str = get_base_secrets().MONGODB_URL
    REDIS_URL: str = "redis://localhost:6379/7"

    # EXTERNAL SERVICES
    OPENAI_API_KEY: str = get_base_secrets().OPENAI_API_KEY
    CONVERT_API_SECRET: str = get_base_secrets().CONVERT_API_SECRET

    # MongoDB Databases and Collections
    MONGODB_COLLECTIONS: ClassVar[MongoDBCollections] = MongoDBCollections()
    MONGODB_DATABASES: ClassVar[MongoDBDatabase] = MongoDBDatabase()

    # AWS S3
    S3_BUCKETS: ClassVar[S3Buckets] = S3Buckets()

    # AWS SQS
    SQS_QUEUES: ClassVar[SQSQueues] = SQSQueues()

    # WEB SOCKET
    WEB_SOCKET_URL: str = get_websocket_secrets().ENDPOINT


config: Config = Config()
openai.api_key = config.OPENAI_API_KEY
convertapi.api_credentials = config.CONVERT_API_SECRET
