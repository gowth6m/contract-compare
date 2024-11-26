from app.contract.contract_controller import ContractController, ContractRepository
from app.user.user_controller import UserController
from app.user.user_repository import UserRepository
from core.aws.s3 import get_s3_client
from core.aws.sqs import get_sqs_client
from core.config import config
from core.database.mongodb import mongodb


class Container:
    """
    Central container to provide dependencies for repositories and controllers.
    Provides static access to dependencies.
    """

    @classmethod
    def get_s3_client(cls):
        s3_client = get_s3_client()
        return s3_client

    @classmethod
    def get_sqs_client(cls):
        sqs_client = get_sqs_client()
        return sqs_client

    @classmethod
    async def get_user_repository(cls) -> UserRepository:
        collection = await mongodb.get_collection(
            config.MONGODB_DATABASES.CORE, config.MONGODB_COLLECTIONS.USERS
        )
        return UserRepository(collection)

    @classmethod
    async def get_contract_repository(cls) -> ContractRepository:
        upload_files_collection = await mongodb.get_collection(
            config.MONGODB_DATABASES.CORE, config.MONGODB_COLLECTIONS.UPLOAD_FILES
        )
        upload_batches_collection = await mongodb.get_collection(
            config.MONGODB_DATABASES.CORE, config.MONGODB_COLLECTIONS.UPLOAD_BATCHES
        )
        contract_reviews_collection = await mongodb.get_collection(
            config.MONGODB_DATABASES.CORE, config.MONGODB_COLLECTIONS.CONTRACT_REVIEWS
        )

        contract_process_connections_collection = await mongodb.get_collection(
            config.MONGODB_DATABASES.CORE,
            config.MONGODB_COLLECTIONS.CONTRACT_PROCESS_CONNECTIONS,
        )

        return ContractRepository(
            upload_files_collection,
            upload_batches_collection,
            contract_reviews_collection,
            contract_process_connections_collection,
        )

    @classmethod
    async def get_user_controller(cls) -> UserController:
        user_repo = await cls.get_user_repository()
        return UserController(user_repo=user_repo)

    @classmethod
    async def get_contract_controller(cls) -> ContractController:
        contract_repo = await cls.get_contract_repository()
        s3_client = cls.get_s3_client()
        sqs_client = cls.get_sqs_client()
        return ContractController(
            contract_repo=contract_repo, s3_client=s3_client, sqs_client=sqs_client
        )
