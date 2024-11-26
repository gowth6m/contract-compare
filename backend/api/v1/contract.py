from typing import List, Optional

from fastapi import APIRouter, Depends, File, Path, Query
from fastapi import UploadFile as FastAPIUploadFile

from app.container import Container
from app.contract.contract_controller import ContractController
from app.contract.contract_models import (
    CompareContractsRequest,
    ContractReview,
    UploadBatchExpanded,
    UploadFile,
)
from app.user.user_models import User
from core.dependencies.authentication import AuthenticationRequired
from core.dependencies.current_user import get_current_user
from core.exceptions.base import InternalServerErrorException

contract_router = APIRouter()


@contract_router.post(
    "/upload",
    response_model=UploadBatchExpanded,
    dependencies=[Depends(AuthenticationRequired)],
)
async def upload_contracts(
    files: List[FastAPIUploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.upload_contracts(
            current_user=current_user,
            files=files,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.get(
    "/upload/all",
    response_model=List[UploadFile],
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_all_uploaded_contracts(
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.get_all_uploaded_contracts(
            current_user=current_user,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.get(
    "/upload/{file_id}",
    response_model=UploadFile,
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_uploaded_contract_by_id(
    file_id: str = Path(..., title="The ID of the uploaded file"),
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.get_uploaded_contract_by_id(
            current_user=current_user,
            file_id=file_id,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.get(
    "/all",
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_all_reviews(
    current_user: User = Depends(get_current_user),
    page: Optional[int] = Query(
        None, description="The page number to retrieve", ge=1, title="Page Number"
    ),
    limit: Optional[int] = Query(
        None, description="The number of items to retrieve", ge=1, title="Limit"
    ),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.get_all_reviews(
            current_user=current_user,
            page=page,
            limit=limit,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.post(
    "/compare",
    dependencies=[Depends(AuthenticationRequired)],
    response_model=List[ContractReview],
)
async def compare_contracts(
    payload: CompareContractsRequest,
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.compare_contracts(
            current_user=current_user,
            contract_ids=payload.ids,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.get(
    "/{review_id}",
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_review_by_id(
    review_id: str = Path(..., title="The ID of review"),
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.get_review_by_id(
            current_user=current_user,
            review_id=review_id,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))


@contract_router.get(
    "/batch/{batch_id}",
    dependencies=[Depends(AuthenticationRequired)],
)
async def get_batch_by_id(
    batch_id: str = Path(..., title="The ID of batch"),
    current_user: User = Depends(get_current_user),
    contract_controller: ContractController = Depends(
        Container.get_contract_controller
    ),
):
    try:
        response = await contract_controller.get_expanded_batch_by_id(
            current_user=current_user,
            batch_id=batch_id,
        )
        return response
    except Exception as e:
        raise InternalServerErrorException(str(e))
