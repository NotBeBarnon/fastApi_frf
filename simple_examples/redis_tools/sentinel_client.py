# -*- coding: utf-8 -*-
# @Time    : 2022/6/2 9:48
# @Author  : Tuffy
# @Description : 

import asyncio

import aioredis
from loguru import logger


async def aioredis_redis():
    from aioredis import Redis
    redis = Redis(host='10.64.5.70', port=31081, db=0)
    await redis.set('Tuffy', 'this is redis')
    print(await redis.get('Tuffy'))
    redis = Redis(host='10.64.5.70', port=31080, db=0)
    print(await redis.get('Tuffy'))
    redis = Redis(host='10.64.5.70', port=31082, db=0)
    print(await redis.get('Tuffy'))


async def aioredis_sentinel():
    from aioredis.sentinel import Sentinel
    sentinel = Sentinel([('10.64.5.70', 31380), ('10.64.5.70', 31381), ('10.64.5.70', 31382)], sentinel_kwargs={'db': 1})
    master = sentinel.master_for('mymaster')
    await master.set('Tuffy', 'this is redis')
    slave = sentinel.slave_for('mymaster')
    print(await slave.get('Tuffy'))


async def sentinel_test():
    from src.my_tools.redis_tools.clients import RedisNamespace, RedisSentinelClient, SentinelNodeEnum
    sentinel_manager = RedisSentinelClient(
        [("10.64.5.70", 31380), ("10.64.5.70", 31381), ("10.64.5.70", 31382)],
        db=0,
        user="",
        password=""
    )
    sentinel_manager.start()
    await sentinel_manager.wait_connect()
    for _ in range(3):
        try:
            with sentinel_manager.get_client(SentinelNodeEnum.master) as client:
                assert isinstance(client, aioredis.Redis)
                # await client.set(RedisNamespace.key("alive"), b"alive", ex=10)
                async for i_, result in client.hscan_iter("NCC:rcst:timeslot:IN_1:SF_1", count=1):
                    logger.debug(f"Set Redis Successfully {result}")
        except Exception as exc:
            logger.error(f"Set Error - {exc.__class__.__name__}:{exc}")

        await asyncio.sleep(2)
    sentinel_manager.stop()
    await sentinel_manager.wait_stop()
    logger.info("Redis客户端资源释放完毕")


if __name__ == '__main__':
    asyncio.run(sentinel_test())
