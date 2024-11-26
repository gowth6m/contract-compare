import asyncio

from bson import ObjectId

from app.container import Container
from app.contract.contract_models import WebSocketConnection


async def async_lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    user_id = event["queryStringParameters"]["user_id"]

    print(f"User {user_id} connected with connection id {connection_id}")

    connection = WebSocketConnection(
        user_id=ObjectId(user_id),
        connection_id=connection_id,
    )

    contract_repo = await Container.get_contract_repository()
    await contract_repo.save_connection(connection)

    return {"statusCode": 200}


def lambda_handler(event, context):
    print("Received event:", event)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_lambda_handler(event, context))
