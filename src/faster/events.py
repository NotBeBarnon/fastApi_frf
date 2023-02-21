# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:15:37
# @Author  : fzx
# @Description : FastAPI 启动与关闭事件
import asyncio
import contextlib

import async_timeout
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from tortoise import Tortoise

from .apps import fast_app
from ..my_tools.object_manager_tools import global_om
from ..my_tools.redis_tools.clients import RedisSentinelClient
from ..my_tools.schedule_tasks.scheduleUtils import func
from ..settings import DATABASE_CONFIG, DEFAULT_TIMEZONE

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
    logger.info(f"Tortoise-ORM started: {Tortoise.apps}")


@fast_app.on_event("shutdown")
async def close_orm() -> None:  # pylint: disable=W0612
    await Tortoise.close_connections()
    logger.info("Tortoise-ORM shutdown")


@fast_app.on_event('startup')
def init_scheduler():
    """定时任务"""
    global scheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(func,
                      CronTrigger(month='1,4,7,10', day=1, hour=0, minute=0, second=0, timezone=DEFAULT_TIMEZONE))
    logger.debug("启动定时任务...")

    scheduler.start()


@fast_app.on_event("startup")
async def init_redis() -> None:
    redis_client_: RedisSentinelClient = global_om["redis_client"]
    redis_client_.start()
    with contextlib.suppress(asyncio.TimeoutError):
        async with async_timeout.timeout(3) as cm:
            await redis_client_.wait_connect()
