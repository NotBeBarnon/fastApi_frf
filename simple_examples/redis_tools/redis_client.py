# -*- coding: utf-8 -*-
# @Time    : 2022/5/5 11:42
# @Author  : Tuffy
# @Description : 

import asyncio
from typing import List, Tuple

import aioredis
import orjson
from loguru import logger

from src.my_tools.redis_tools.clients import RedisClient, RedisNamespace


async def client_test():
    rc = RedisClient("10.64.5.70", 30079, db=3, user="", password="")
    rc.start()
    await rc.wait_connect()
    for _ in range(5):
        try:
            with rc as client:
                assert isinstance(client, aioredis.Redis)
                await client.set(RedisNamespace.key("alive"), b"alive", ex=10)
                logger.debug(f"Set Redis Successfully {rc}")
        except Exception as exc:
            logger.error(f"Set Error - {exc.__class__.__name__}:{exc}")

        await asyncio.sleep(1)
    with rc as client:
        result_: Tuple = await asyncio.gather(
            client.pttl(RedisNamespace.key("alive")),
            client.pttl(RedisNamespace.key("test")),
            client.pttl(RedisNamespace.key("world")),
            return_exceptions=True,
        )
        logger.debug(f"Get Redis Successfully - {type(result_)}:{result_}")

    rc.stop()
    await rc.wait_stop()
    logger.info("Redis客户端资源释放完毕")


async def redis_client_set():
    rc = RedisClient("localhost", 6379, db=0, user="", password="")
    rc.start()
    await rc.wait_connect()
    with rc as client:
        assert isinstance(client, aioredis.Redis)
        for i in range(5):
            await client.sadd(RedisNamespace.key("set_test"), i)
            logger.debug(f"Set Redis Successfully {rc}")

        values_ = await client.smembers(RedisNamespace.key("set_test"))
        logger.debug(f"Get Redis Successfully - {type(values_)}:{values_}")
        for v_bytes_ in values_:
            v_ = orjson.loads(v_bytes_)
            logger.debug(f"Get Redis Successfully - {type(v_)}:{v_}")
        values_ = await client.smembers(RedisNamespace.key("not_exist_set_test"))
        logger.debug(f"Get Redis Successfully - {type(values_)}:{values_}")
        values_ = await client.srem(RedisNamespace.key("not_exist_set_test"), b"hello")
        logger.debug(f"Get Redis delete result - {values_}")

    rc.stop()
    await rc.wait_stop()
    logger.info("Redis客户端资源释放完毕")


async def redis_client_hash():
    rc = RedisClient("localhost", 6379, db=0, user="", password="")
    rc.start()
    await rc.wait_connect()
    with rc as client:
        if not isinstance(client, aioredis.Redis):
            return
    for i in range(16):
        await client.hset(RedisNamespace.key("hash_test"), i + 1, chr(i + 97))
    cursor_, res_ = await client.hscan(RedisNamespace.key("hash_test"), count=10)
    logger.debug(f"Get hash:{cursor_} {res_}")

    rc.stop()
    await rc.wait_stop()
    logger.info("Redis客户端资源释放完毕")


async def lua_test():
    lua_script = """
    local hash_key = "hash_key"
    local key = KEYS[1]
    local value = ARGV[1]
    redis.call("SET", "name", "Tuffy", "EX", 10)
    local set_result = redis.call("HSET", hash_key, key, value)
    local get_result = redis.call("GET", "helo")
    return { set_result, get_result}
    """
    rc = RedisClient("localhost", 6379, db=0, user="", password="")
    rc.start()
    await rc.wait_connect()
    with rc as client:
        assert isinstance(client, aioredis.Redis)
        result_ = await client.eval(lua_script, 1, orjson.dumps("hello"), orjson.dumps({"k1": 1}))
        print(result_)

    rc.stop()
    await rc.wait_stop()
    logger.info("Redis客户端资源释放完毕")


if __name__ == '__main__':
    asyncio.run(lua_test())
