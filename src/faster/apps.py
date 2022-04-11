# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:14:15
# @Author  : fzx
# @Description : FastAPI的app

from fastapi import FastAPI

from .routers import all_router
from ..settings import HTTP_BASE_URL
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

fast_app.include_router(all_router)
