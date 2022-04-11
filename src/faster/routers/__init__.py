# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:16:29
# @Author  : fzx
# @Description :

from fastapi import Request, APIRouter
from fastapi.responses import ORJSONResponse
from loguru import logger
from pydantic import BaseModel

# from .resource.routers import resource_routers
# from .user.routers import user_routers
from .resource.routers import resource_router
from .users.routers import user_router
from ...settings import HTTP_BASE_URL

__all__ = ()

all_router = APIRouter(prefix=HTTP_BASE_URL)
all_router.include_router(user_router)
all_router.include_router(resource_router)


class FastAPIStatus(BaseModel):
    message: str = "FastAPI success!"


@all_router.get(
    "/check",
    summary="验活",
    response_class=ORJSONResponse,
    response_model=FastAPIStatus,
    response_description="验活成功响应",
)
def home(request: Request):
    logger.debug(f"Request from [{request.client}]")
    return FastAPIStatus()

