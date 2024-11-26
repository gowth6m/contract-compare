from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from core.config import config


class MongoDB:
    """A wrapper for managing a MongoDB client instance."""

    _client: Optional[AsyncIOMotorClient] = None

    @classmethod
    async def connect(cls):
        """Initialize the MongoDB client if not already connected."""
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(
                    str(config.MONGODB_URL),
                    maxPoolSize=10,
                    minPoolSize=0,
                    connectTimeoutMS=10000,
                )
                # Verify the connection with a ping
                await cls._client.admin.command("ping")
                print("MongoDB connection established.")
            except Exception as e:
                cls._client = None
                print(f"Error connecting to MongoDB: {e}")
                raise RuntimeError("Failed to connect to MongoDB.") from e

    @classmethod
    def close(cls):
        """Close the MongoDB client connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            print("MongoDB connection closed.")

    @classmethod
    async def get_client(cls) -> AsyncIOMotorClient:
        """Return the MongoDB client, initializing it if necessary."""
        if cls._client is None:
            await cls.connect()
        return cls._client

    @classmethod
    async def get_database(cls, database_name: str):
        """Return the specified MongoDB database."""
        client = await cls.get_client()
        return client[database_name]

    @classmethod
    async def get_collection(cls, database_name: str, collection_name: str):
        """Return the specified MongoDB collection."""
        database = await cls.get_database(database_name)
        return database[collection_name]


mongodb = MongoDB()
