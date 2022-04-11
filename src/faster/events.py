# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:15:37
# @Author  : fzx
# @Description : FastAPI 启动与关闭事件

from loguru import logger
from tortoise import Tortoise

from .apps import fast_app
from ..settings import DATABASE_CONFIG

__all__ = ()


@fast_app.on_event("startup")
async def startup() -> None:
    logger.info(f"Startup: Message")


@fast_app.on_event("shutdown")
async def shutdown() -> None:
    logger.info(f"Shutdown: Message")


@fast_app.on_event("startup")
async def init_orm() -> None:  # pylint: disable=W0612
    await Tortoise.init(config=DATABASE_CONFIG)
    logger.info(f"Tortoise-ORM started: {Tortoise._connections} ----- {Tortoise.apps}")


@fast_app.on_event("shutdown")
async def close_orm() -> None:  # pylint: disable=W0612
    await Tortoise.close_connections()
    logger.info("Tortoise-ORM shutdown")
