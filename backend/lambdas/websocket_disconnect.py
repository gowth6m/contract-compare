import asyncio

from app.container import Container


async def async_lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]

    print(f"User disconnected with connection id {connection_id}")

    contract_repo = await Container.get_contract_repository()
    await contract_repo.delete_connection(connection_id.to_string())

    return {"statusCode": 200}


def lambda_handler(event, context):
    print("Received event:", event)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_lambda_handler(event, context))
