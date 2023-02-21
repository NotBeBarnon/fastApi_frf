# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:14:15
# @Author  : fzx
# @Description : FastAPI的app

from fastapi import FastAPI

from .routers import all_router
from ..my_tools.object_manager_tools import global_om
from ..my_tools.redis_tools.clients import RedisSentinelClient
from ..settings import HTTP_BASE_URL, REDIS_CONFIG
from ..version import VERSION

__all__ = (
    "fast_app",
)

fast_app = FastAPI(
    title="FastSample",
    description="FastAPI 示例项目",
    version=VERSION,
    openapi_url=f"{HTTP_BASE_URL}/openapi.json",
    docs_url=f"{HTTP_BASE_URL}/docs",
    redoc_url=f"{HTTP_BASE_URL}/redoc",
)

redis_client_ = RedisSentinelClient(
    sentinels=REDIS_CONFIG["sentinels"]["service"],
    service_name=REDIS_CONFIG["sentinels"]["service_name"],
    db=REDIS_CONFIG["db"],
    user=REDIS_CONFIG["user"],
    password=REDIS_CONFIG["password"],
    retry_interval=REDIS_CONFIG["retry_interval"],
)
global_om.register("redis_client", redis_client_)

fast_app.include_router(all_router)
