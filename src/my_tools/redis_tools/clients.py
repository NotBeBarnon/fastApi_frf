# -*- coding: utf-8 -*-
# @Time    : 2023/2/17:14:40
# @Author  : fzx
# @Description : redis 哨兵模式使用, 客户端连接
import abc
import asyncio
import contextlib
import hashlib
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Tuple, Any, Union, Callable, Iterator, Set

import aioredis
from aioredis.sentinel import Sentinel
from loguru import logger
from fastapi.responses import Response
from src.my_tools.singleton_tools import SingletonABCMeta
from src.settings import REDIS_CONFIG

CLEAN_LUA_SCRIPT = """
        local cursor = "0"
        repeat
            local result = redis.call("SCAN", cursor, "MATCH", ARGV[1], "COUNT", 10)
            cursor = result[1]
            for _, key in ipairs(result[2]) do
                redis.call("del", key)
            end
        until cursor == "0"
        """


class RedisNamespaceABC(metaclass=SingletonABCMeta):

    @property
    @abc.abstractmethod
    def namespace(self) -> bytes:
        ...

    @classmethod
    def get_namespace(cls) -> str:
        return cls.namespace.decode("utf-8")

    @classmethod
    def get_namespace_bytes(cls) -> bytes:
        return cls.namespace

    @classmethod
    def key(cls, key: Union[str, bytes]) -> bytes:
        if isinstance(key, str):
            key = key.encode("utf-8")
        return cls.namespace + b":" + key

    @classmethod
    def hash_http_cache_key(cls, route: str, query: str = None) -> bytes:
        if query:
            m = hashlib.md5()
            m.update(query.encode("utf-8"))
            hash_query = m.hexdigest().encode("utf-8")
        else:
            hash_query = b""
        # 如果是GET请求，则进行缓存逻辑
        return cls.namespace + b":http_cache:" + route.encode("utf-8") + b":" + hash_query

    @classmethod
    def get_all_keys_by_route(cls, route: str) -> str:
        return cls.namespace.decode("utf-8") + ":" + route + "*"


@dataclass(frozen=True)
class RedisNamespace(RedisNamespaceABC):
    namespace = REDIS_CONFIG["namespace"].encode("utf-8")


@dataclass
class RedisClient:
    """
    Redis客户端
    - host
    - port
    - user : 账号
    - password : 密码
    - group : 消费者组
    - retry_interval : 重连间隔 单位秒
    """
    host: str
    port: int
    db: int
    user: str
    password: str
    retry_interval: int
    conn_alive_flag: bool = False
    __conn_success_event: asyncio.Event = None
    __conn_alive_event: asyncio.Event = None
    __conn_stop_event: asyncio.Event = None

    def __init__(
            self,
            host: str,
            port: int,
            db: int,
            *,
            user: str = None,
            password: str = None,
            retry_interval: int = 10,
            **kwargs,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.db = db
        self.user = user or None
        self.password = password or None
        self.retry_interval = retry_interval
        self.__pass_param = kwargs

        self.__pool_client: aioredis.Redis = None  # Redis连接池客户端

    def set_host(self, host: str, port: int) -> Tuple[str, int]:
        pre_ = (self.host, self.port)
        now_ = (host, port)
        if pre_ != now_:
            # 重新设置host，并重启
            self.host = host
            self.port = port
            self.restart()

        return self.host, self.port

    async def __init_redis(self):
        self.__pool_client = None
        while self.conn_alive_flag:
            logger.info(
                f"Connect Redis<{self.user}:{self.password}@{self.host}:{self.port}>, _RedisClient__conn_success_event={self.__conn_success_event}")
            try:
                pool_client_: aioredis.Redis = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    username=self.user,
                    password=self.password,
                    **self.__pass_param
                )

                await pool_client_.set(RedisNamespace.get_namespace_bytes(), b"alive", ex=self.retry_interval * 2)
                self.__pool_client = pool_client_

                self.__conn_success_event.set()
                logger.success(
                    f"Successfully connect Redis<{self.user}:{self.password}@{self.host}:{self.port}>, _RedisClient__conn_success_event={self.__conn_success_event}"
                )
                break
            except Exception as exc:
                logger.warning(
                    f"Failed to connect Redis<{self.user}:{self.password}@{self.host}:{self.port}>: {exc.__class__.__name__}:{exc}")
                await asyncio.sleep(self.retry_interval)

    async def __start(self):
        if not self.__conn_stop_event.is_set():
            # __conn_stop_event没有被标记，说明任务还没有结束，无需重复启动
            logger.warning(
                f"Redis<{self.user}:{self.password}@{self.host}:{self.port}> is already running, _RedisClient__conn_alive_event={self.__conn_alive_event}"
            )
            return

        self.__conn_stop_event.clear()  # 清除标记，代表任务开始
        logger.success(f"Redis<{self.user}:{self.password}@{self.host}:{self.port}> begin start ...")
        while self.conn_alive_flag:
            self.__conn_alive_event.clear()
            self.__conn_success_event.clear()
            await self.__init_redis()

            await self.__conn_alive_event.wait()
            if isinstance(self.__pool_client, aioredis.Redis):
                logger.warning(
                    f"Redis<{self.user}:{self.password}@{self.host}:{self.port}> disconnected ... reconnect={self.conn_alive_flag}")
                redis_client = self.__pool_client
                self.__pool_client = None
                await redis_client.close()  # 此处等待资源释放

        self.__conn_stop_event.set()  # 标记任务结束
        self.__conn_success_event.set()
        self.__conn_alive_event.set()
        logger.warning(f"Redis<{self.user}:{self.password}@{self.host}:{self.port}> client stopped")

    def __stop(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            self.__conn_success_event.clear()
        if isinstance(self.__conn_alive_event, asyncio.Event):
            self.__conn_alive_event.set()

    async def wait_connect(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            await self.__conn_success_event.wait()

    async def wait_stop(self):
        if isinstance(self.__conn_stop_event, asyncio.Event):
            await self.__conn_stop_event.wait()

    def start(self):
        """
        必须异步启动，但是会额外提交一个__start的task到事件循环中
        """
        self.conn_alive_flag = True
        if not isinstance(self.__conn_stop_event, asyncio.Event):
            self.__conn_alive_event = asyncio.Event()
            self.__conn_success_event = asyncio.Event()
            self.__conn_stop_event = asyncio.Event()
        # 设置启动初始状态
        self.__conn_stop_event.set()
        self.__conn_alive_event.clear()
        self.__conn_success_event.clear()
        asyncio.create_task(self.__start())

    def stop(self):
        self.conn_alive_flag = False
        logger.warning(f"Call Stop {self}")
        self.__stop()

    def restart(self):
        logger.warning(f"Call Restart {self}")
        self.__stop()

    def get_client(self, node: Any):
        return self

    def client(self, node: Any) -> aioredis.Redis:
        return self.__pool_client

    def __enter__(self) -> aioredis.Redis:
        return self.__pool_client

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理redis连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if exc_type is None:
            return False

        if isinstance(exc_val, (aioredis.ConnectionError, aioredis.TimeoutError)):
            logger.error(f"Redis Error {exc_type}:{exc_val}")
            self.restart()
            return True

        if isinstance(exc_val, AssertionError):
            # Redis客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"RedisClient -- {exc_type}:{exc_val}")
            return True

        return False

    async def __aenter__(self) -> aioredis.Redis:
        return self.__pool_client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理redis连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if exc_type is None:
            return False

        if isinstance(exc_val, (aioredis.ConnectionError, aioredis.TimeoutError)):
            logger.error(f"Redis Error {exc_type}:{exc_val}")
            self.restart()
            return True

        if isinstance(exc_val, AssertionError):
            # Redis客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"RedisClient -- {exc_type}:{exc_val}")
            return True

        return False

    def __call__(self, key: Union[bytes, str], response: Response, ex_pttl: int = 3000) -> Callable:
        """
        针对FastAPI的缓存装饰器，如果是位置使用，请修改response参数
        :param key: 访问的key
        :param ex_pttl: 缓存过期时间，单位毫秒
        :param response: 响应对象
        :return:
        """

        def decorator_(func: Callable) -> Callable:
            @wraps(func)
            async def cache_wrapper_(*args_, **kwargs_):
                if isinstance(self.__pool_client, aioredis.Redis):
                    with contextlib.suppress(Exception):
                        value = await self.__pool_client.get(key)
                        if value is not None:
                            await self.__pool_client.pexpire(key, ex_pttl)
                            response.body = value
                            return response
                return await func(*args_, **kwargs_)

            return cache_wrapper_

        return decorator_

    async def clean_cache_for_route(self, route: str):
        try:
            await self.__pool_client.eval(
                CLEAN_LUA_SCRIPT, 0, RedisNamespace.get_all_keys_by_route(route)
            )
        except Exception as e:
            logger.error(e)
            return False
        return True


class SentinelNodeEnum(str, Enum):
    master = "MASTER"
    slave = "SLAVE"


@dataclass
class RedisSentinelClient:
    sentinels: Set[Tuple[str, int]]
    service_name: str
    db: int = 0,
    user: str = None,
    password: str = None,
    retry_interval: int = 10
    conn_alive_flag: bool = False
    __conn_success_event: asyncio.Event = None
    __conn_alive_event: asyncio.Event = None
    __conn_stop_event: asyncio.Event = None

    def __init__(
            self,
            sentinels: Iterator[Tuple[str, int]],
            *,
            service_name: str = "mymaster",
            db: int = 0,
            user: str = None,
            password: str = None,
            retry_interval: int = 10,
            **kwargs,
    ):
        super().__init__()
        self.sentinels = set(sentinels)
        self.service_name = service_name
        self.db = db
        self.user = user or None
        self.password = password or None
        self.retry_interval = retry_interval
        self.__pass_param = kwargs

        self.__sentinel_manager: Sentinel = None  # 哨兵客户端
        self.__node: str = None  # 哨兵节点类型
        self.__master_redis: aioredis.Redis = None
        self.__slave_redis: aioredis.Redis = None

    async def __init_redis(self):
        self.__sentinel_manager = None
        while self.conn_alive_flag:
            logger.info(
                f"Connect Redis<{self.user}:{self.password}@{self.sentinels}>, _RedisSentinelClient__conn_success_event={self.__conn_success_event}")
            try:
                sentinel_: Sentinel = Sentinel(
                    sentinels=self.sentinels,
                    db=self.db,
                    password=self.password,
                    username=self.user,
                    **self.__pass_param,
                )
                master_redis: aioredis.Redis = sentinel_.master_for(self.service_name)
                await master_redis.set(RedisNamespace.get_namespace_bytes(), b"alive", ex=self.retry_interval * 2)
                self.__sentinel_manager = sentinel_
                self.__master_redis = master_redis
                self.__slave_redis = sentinel_.slave_for(self.service_name)

                self.__conn_success_event.set()
                logger.success(
                    f"Successfully connect Redis<{self.user}:{self.password}@{self.sentinels}>,"
                    f" _RedisSentinelClient__conn_success_event={self.__conn_success_event}"
                )
                break
            except Exception as exc:
                logger.warning(
                    f"Failed to connect Redis<{self.user}:{self.password}@{self.sentinels}>: {exc.__class__.__name__}:{exc}")
                await asyncio.sleep(self.retry_interval)

    async def __start(self):
        if not self.__conn_stop_event.is_set():
            # __conn_stop_event没有被标记，说明任务还没有结束，无需重复启动
            logger.warning(
                f"Redis<{self.user}:{self.password}@{self.sentinels}> is already running,"
                f" _RedisSentinelClient__conn_alive_event={self.__conn_alive_event}"
            )
            return

        self.__conn_stop_event.clear()  # 清除标记，代表任务开始
        logger.success(f"Redis<{self.user}:{self.password}@{self.sentinels}> begin start ...")
        while self.conn_alive_flag:
            self.__conn_alive_event.clear()
            self.__conn_success_event.clear()
            await self.__init_redis()

            await self.__conn_alive_event.wait()
            if isinstance(self.__sentinel_manager, Sentinel):
                logger.warning(
                    f"Redis<{self.user}:{self.password}@{self.sentinels}> disconnected ... reconnect={self.conn_alive_flag}")
                sentinel_manager_ = self.__sentinel_manager
                self.__sentinel_manager = None
                _ = await asyncio.gather(
                    *[
                        redis_.close()
                        for redis_ in sentinel_manager_.sentinels
                    ],
                    return_exceptions=True
                )

        self.__conn_stop_event.set()  # 标记任务结束
        self.__conn_success_event.set()
        self.__conn_alive_event.set()
        logger.warning(f"Redis<{self.user}:{self.password}@{self.sentinels}> client stopped")

    def __stop(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            self.__conn_success_event.clear()
        if isinstance(self.__conn_alive_event, asyncio.Event):
            self.__conn_alive_event.set()

    async def wait_connect(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            await self.__conn_success_event.wait()

    async def wait_stop(self):
        if isinstance(self.__conn_stop_event, asyncio.Event):
            await self.__conn_stop_event.wait()

    def start(self):
        """
        必须异步启动，但是会额外提交一个__start的task到事件循环中
        """
        self.conn_alive_flag = True
        if not isinstance(self.__conn_stop_event, asyncio.Event):
            self.__conn_alive_event = asyncio.Event()
            self.__conn_success_event = asyncio.Event()
            self.__conn_stop_event = asyncio.Event()
        # 设置启动初始状态
        self.__conn_stop_event.set()
        self.__conn_alive_event.clear()
        self.__conn_success_event.clear()
        asyncio.create_task(self.__start())

    def stop(self):
        self.conn_alive_flag = False
        logger.warning(f"Call Stop {self}")
        self.__stop()

    def restart(self):
        logger.warning(f"Call Restart {self}")
        self.__stop()

    def get_client(self, node: SentinelNodeEnum):
        self.__node = node
        return self

    def client(self, node: SentinelNodeEnum) -> aioredis.Redis:
        if node == SentinelNodeEnum.master:
            return self.__master_redis
        elif node == SentinelNodeEnum.slave:
            return self.__slave_redis

    def __enter__(self) -> aioredis.Redis:
        if not isinstance(self.__sentinel_manager, Sentinel):
            return None
        if self.__node == SentinelNodeEnum.master:
            return self.__master_redis
        elif self.__node == SentinelNodeEnum.slave:
            return self.__slave_redis

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理redis连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if exc_type is None:
            return False

        if isinstance(exc_val, (aioredis.ConnectionError, aioredis.TimeoutError)):
            logger.error(f"Redis Error {exc_type}:{exc_val}")
            return True

        if isinstance(exc_val, AssertionError):
            # Redis客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"RedisClient -- {exc_type}:{exc_val}")
            return True

        return False

    async def __aenter__(self) -> aioredis.Redis:
        if not isinstance(self.__sentinel_manager, Sentinel):
            return None
        if self.__node == SentinelNodeEnum.master:
            return self.__master_redis
        elif self.__node == SentinelNodeEnum.slave:
            return self.__slave_redis

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理redis连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if exc_type is None:
            return False

        if isinstance(exc_val, (aioredis.ConnectionError, aioredis.TimeoutError)):
            logger.error(f"Redis Error {exc_type}:{exc_val}")
            return True

        if isinstance(exc_val, AssertionError):
            # Redis客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"RedisClient -- {exc_type}:{exc_val}")
            return True

        return False

    def __call__(self, key: Union[bytes, str], response: Response, ex_pttl: int = 3000) -> Callable:
        def decorator_(func: Callable) -> Callable:
            @wraps(func)
            async def cache_wrapper_(*args_, **kwargs_):
                if isinstance(self.__sentinel_manager, Sentinel):
                    with contextlib.suppress(Exception):
                        node_client_ = self.__sentinel_manager.slave_for(self.service_name)
                        value = await node_client_.get(key)
                        if value is not None:
                            await self.__sentinel_manager.master_for(self.service_name).pexpire(key, ex_pttl)
                            response.body = value
                            return response
                return await func(*args_, **kwargs_)

            return cache_wrapper_

        return decorator_

    async def clean_cache_for_route(self, route: str):
        try:
            await self.__sentinel_manager.master_for(self.service_name).eval(
                CLEAN_LUA_SCRIPT, 0, RedisNamespace.get_all_keys_by_route(route)
            )
        except Exception as e:
            logger.error(e)
            return False
        return True
