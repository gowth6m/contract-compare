import asyncio

from app.container import Container
from app.contract.contract_controller import ContractController


async def async_lambda_handler(event, context):
    contract_repo = await Container.get_contract_repository()
    s3_client = Container.get_s3_client()
    sqs_client = Container.get_sqs_client()
    contract_controller = ContractController(
        contract_repo=contract_repo, s3_client=s3_client, sqs_client=sqs_client
    )

    await contract_controller.process_uploaded_files(event)

    return {"statusCode": 200, "body": "Files processed successfully"}


def lambda_handler(event, context):
    print("Received event:", event)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(async_lambda_handler(event, context))
