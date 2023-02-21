# -*- coding: utf-8 -*-
# @Time    : 2022/3/14 15:26
# @Author  : Tuffy
# @Description :
import asyncio
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple, Type, Union

import aiokafka
import async_timeout
from aiokafka import AIOKafkaClient, AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.conn import AIOKafkaConnection
from kafka.admin import NewTopic
from kafka.errors import KafkaConnectionError, KafkaTimeoutError
from kafka.protocol.admin import CreateTopicsRequest_v1, CreateTopicsResponse_v1, DeleteTopicsRequest_v1
from kafka.protocol.metadata import MetadataRequest_v1, MetadataResponse_v1
from loguru import logger

from src.settings import MQ_CONFIG
from .callbacks import BaseTopicCall


@dataclass
class TopicConfig(NewTopic):
    name: str
    num_partitions: int
    replication_factor: int
    topic_configs: Dict = None

    def __init__(
        self,
        name,
        num_partitions,
        replication_factor=0,
        replica_assignments=None,
        topic_configs=None,
    ):
        super().__init__(name, num_partitions, replication_factor, replica_assignments, topic_configs)


@dataclass
class CreateTopicMixin:
    num_partitions = MQ_CONFIG["num_partitions"]
    replication_factor = MQ_CONFIG["replication_factor"]
    topic_configs = MQ_CONFIG["topic_configs"]

    create_topic_timeout = 3
    created_topics: Set
    exist_topics: Set

    def __init__(self):
        self.topics_conf: Dict[str, NewTopic] = {}  # 所有主题的配置
        self.controller_node_id = None  # Kafka的控制节点
        self.created_topics = set()
        self.exist_topics = set()

    def set_topics_conf(self, conf: Dict[str, NewTopic]):
        """
        设置主题配置
        Args:
            conf: 新建主题配置
                {
                    "topic_name": NewTopic,
                    ...
                }
        """
        self.topics_conf.update(conf)

    async def _get_controller_node_id(self, client: AIOKafkaClient):
        """
        查找Kafka的控制节点
        """

        nodes_id_ = [b_.nodeId for b_ in client.cluster.brokers()]

        for node_id_ in nodes_id_:
            conn_: AIOKafkaConnection = await client._get_conn(node_id_)
            # fut_ = await conn_.send(MetadataRequest[1]())
            fut_: MetadataResponse_v1 = await conn_.send(MetadataRequest_v1())
            self.controller_node_id = fut_.controller_id
            break

        return self.controller_node_id

    async def _get_topics(self, client: AIOKafkaClient) -> Set[str]:
        nodes_id_ = [b_.nodeId for b_ in client.cluster.brokers()]
        topics_name_set: Set[str] = set()
        for node_id_ in nodes_id_:
            conn_: AIOKafkaConnection = await client._get_conn(node_id_)
            fut_: MetadataResponse_v1 = await conn_.send(MetadataRequest_v1())
            topics_name_set = {name for _, name, _, _ in fut_.topics}
            break

        self.exist_topics |= topics_name_set
        return topics_name_set

    async def _delete_topics(self, client: AIOKafkaClient, topics_name_set: Iterator[str]) -> Tuple[Set[str], Dict[str, int]]:
        delete_topics_request_ = DeleteTopicsRequest_v1(
            topics=topics_name_set,
            timeout=3000,  # 单位毫秒
        )
        controller_node_id_ = await self._get_controller_node_id(client)
        conn_: AIOKafkaConnection = await client._get_conn(controller_node_id_)
        fut_: CreateTopicsResponse_v1 = await conn_.send(delete_topics_request_)

        resp_data_ = fut_.to_object()
        success_ = set()
        failed_ = {}
        [
            failed_.update({item_["topic"]: item_["error_code"]})
            if item_["error_code"] else
            success_.add(item_["topic"])
            for item_ in resp_data_["topic_error_codes"]
        ]
        self.exist_topics -= success_
        self.created_topics -= success_
        return success_, failed_

    async def _create_topics(self, client: AIOKafkaClient, conf: List[NewTopic]) -> Tuple[Set[str], Dict[str, Tuple[int, str]]]:
        """
        创建主题  此方法与_get_topics_list、_delete_topics相同，不会对类内的配置产生任何影响，是附加方法
        _auto_create_topics方法为自动创建Topic的方法，会对类内的配置产生影响
        """
        new_topics_request_ = CreateTopicsRequest_v1(
            create_topic_requests=[
                self.convert_new_topic_request(new_topic)
                for new_topic in conf
            ],
            timeout=3000,  # 单位毫秒
        )

        controller_node_id = await self._get_controller_node_id(client)
        # 创建主题
        conn_: AIOKafkaConnection = await client._get_conn(controller_node_id)
        fut_: CreateTopicsResponse_v1 = await conn_.send(new_topics_request_)

        resp_data_ = fut_.to_object()
        success_ = set()
        failed_ = {}
        [
            failed_.update({item_["topic"]: (item_["error_code"], item_["error_message"])})
            if item_["error_code"]
            else success_.add(item_["topic"])
            for item_ in resp_data_["topic_errors"]
        ]

        exist_topics_ = {
            topic_
            for topic_, (code_, msg_) in failed_.items()
            if code_ == 36
        }

        success_ |= exist_topics_
        self.exist_topics |= success_
        self.created_topics |= success_
        return success_, failed_

    async def _auto_create_topics(self, client: AIOKafkaClient, conf: Dict[str, NewTopic], *, start_client: bool = False):
        """
        用与在Consumer启动前或者Producer生成消息前自动创建主题
        Args:
            client: 启动了的kafka客户端
            conf: 需要新建的主题及其Topic配置
            start_client: 是否需要自动启动和关闭 client[AIOKafkaClient]
        """
        self.topics_conf.update(conf)

        # 检查版本
        # api_version_ = await client.check_version(node_id_)
        # meta_version_ = 0 if api_version_ < (0, 10) else 1
        logger.info(f"Create Topics: {conf.keys()}")
        # new_topics_request_ = CreateTopicsRequest[1](
        new_topics_request_ = CreateTopicsRequest_v1(
            create_topic_requests=[
                self.convert_new_topic_request(new_topic)
                for new_topic in conf.values()
            ],
            timeout=self.create_topic_timeout * 1000,  # 单位毫秒
        )

        async with async_timeout.timeout(self.create_topic_timeout):
            if start_client:
                await client.bootstrap()

            controller_node_id = await self._get_controller_node_id(client)
            # 创建主题
            conn_: AIOKafkaConnection = await client._get_conn(controller_node_id)
            fut_: CreateTopicsResponse_v1 = await conn_.send(new_topics_request_)

        if start_client:
            await client.close()

        resp_data_ = fut_.to_object()
        success_ = set()
        failed_ = {}
        [
            failed_.update({item_["topic"]: (item_["error_code"], item_["error_message"])})
            if item_["error_code"] else
            success_.add(item_["topic"])
            for item_ in resp_data_["topic_errors"]
        ]

        exist_topics_ = {
            topic_
            for topic_, (code_, msg_) in failed_.items()
            if code_ == 36
        }

        success_ |= exist_topics_
        self.exist_topics |= success_
        self.created_topics |= success_

        success_ and logger.success(f"Create Topics Success: {success_}")
        failed_ and logger.warning(f"Create Topics Failed: {failed_}")

    @classmethod
    def convert_new_topic_request(cls, new_topic: NewTopic) -> Tuple:
        return (
            new_topic.name,
            new_topic.num_partitions,
            new_topic.replication_factor,
            [(partition_id, replicas) for partition_id, replicas in new_topic.replica_assignments.items()],
            [(config_key, config_value) for config_key, config_value in new_topic.topic_configs.items()],
        )


@dataclass
class KafkaConsumerClient(CreateTopicMixin):
    """
    Kafka 消费者客户端
    - host : kafka控制节点地址
    - port : kafka控制节点的端口号
    - user : 账号
    - password : 密码
    - group : 消费者组
    - retry_interval : 重连间隔 单位秒
    - from_now : 是否从建立连接时间开始消费
    - async_callbacks : 是否异步执行Callbacks回调，如果设置为True，回调将使用create_task执行
    """
    bootstrap_servers: Set[str]
    user: str
    password: str
    group: str
    retry_interval: int
    from_now: bool
    async_callbacks: bool
    __pass_param: Dict

    conn_alive_flag: bool = False  # 保持连接的标记
    __conn_success_event: asyncio.Event = None  # 任务开始事件，防止重复启动
    __conn_alive_event: asyncio.Event = None  # 连接成功事件，标记连接任务已经成功连接到Kafka
    __conn_stop_event: asyncio.Event = None  # 任务结束事件

    is_create_topics: bool = False

    def __init__(
        self,
        bootstrap_servers: Iterator[str],
        *,
        user: str = None,
        password: str = None,
        group: str = None,
        retry_interval: int = 10,
        from_now: bool = True,
        async_callbacks: bool = False,
        **kwargs,
    ):
        super().__init__()
        self.bootstrap_servers = set(bootstrap_servers)
        self.user = user or None
        self.password = password or None
        self.group = group or None
        self.retry_interval = retry_interval
        self.from_now = from_now
        self.async_callbacks = async_callbacks
        self.__pass_param = kwargs

        self.__consumer: AIOKafkaConsumer = None

        self.__callbacks: Dict[str, type] = {}  # key为kafka的topic，value为BaseTopicCall的子类

    def update_bootstrap_servers(self, new_bootstrap_servers: Iterator[str]):
        new_set_ = set(new_bootstrap_servers)
        if not new_set_ <= self.bootstrap_servers:
            self.topics_need_create()
        self.bootstrap_servers = new_set_
        return self

    def topics_need_create(self) -> "KafkaConsumerClient":
        self.is_create_topics = False
        return self

    def register_callbacks(self, calls: List[Type[BaseTopicCall]]):
        """
        注册接收队列消息的回调
        """
        registered_: Set = set()
        unregistered_: Set = set()
        logger.debug("-----  Kafka Register Consumer  -------")

        for topic_config_item_ in calls:
            if issubclass(topic_config_item_, BaseTopicCall):
                logger.debug(f"Kafka register Consumer <Topic:{topic_config_item_.topic} {topic_config_item_.__name__}>")
                self.__callbacks[topic_config_item_.topic] = topic_config_item_

                # 注册Topic成功，添加NewTopic到topics_conf
                self.topics_conf[topic_config_item_.topic] = NewTopic(
                    name=topic_config_item_.topic,
                    num_partitions=self.num_partitions,
                    replication_factor=self.replication_factor,
                    topic_configs=self.topic_configs,
                )
                registered_.add(topic_config_item_)
            else:
                unregistered_.add(topic_config_item_)
        registered_ and logger.success(f"KafkaConsumer <Registered-{registered_}>") and self.topics_need_create()
        unregistered_ and logger.error(f"KafkaConsumer <Unregistered-{unregistered_}>")
        return registered_, unregistered_

    async def __init_consumer(self):
        self.__consumer = None
        while self.conn_alive_flag:
            logger.info(
                f"Connect KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}>, _KafkaConsumerClient__conn_success_event={self.__conn_success_event}"
            )
            try:

                # 启动之前要先保证Topic存在
                if self.is_create_topics is False:
                    await self._auto_create_topics(
                        AIOKafkaClient(
                            bootstrap_servers=self.bootstrap_servers,
                            sasl_plain_username=self.user,
                            sasl_plain_password=self.password,
                        ),
                        self.topics_conf,
                        start_client=True,
                    )
                    self.is_create_topics = True

                consumer_ = AIOKafkaConsumer(
                    *self.created_topics,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group,
                    sasl_plain_username=self.user,
                    sasl_plain_password=self.password,
                    **self.__pass_param,
                )

                await consumer_.start()
                # 启动后调整offset
                if self.from_now:
                    try:
                        await consumer_.seek_to_end()
                    except Exception as exc:
                        logger.warning(f"Kafka Consumer seek_to_end failed - {exc.__class__.__name__}:{exc}")
                self.__consumer = consumer_

                self.__conn_success_event.set()
                logger.success(
                    f"Successfully connect KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}>, _KafkaConsumerClient__conn_success_event={self.__conn_success_event}"
                )
                break
            except Exception as exc:
                logger.warning(f"Failed to connect KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> - {exc.__class__.__name__}:{exc}")
                await asyncio.sleep(self.retry_interval)

    async def __listening_consumer(self):
        try:
            if self.async_callbacks:
                async for msg in self.__consumer:
                    asyncio.create_task(self.__callback(msg))
            else:
                async for msg in self.__consumer:
                    await self.__callback(msg)
        finally:
            logger.warning(
                f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> listening stop, _KafkaConsumerClient__conn_alive_event={self.__conn_alive_event}"
            )
            if isinstance(self.__consumer, AIOKafkaConsumer):
                await self.__consumer.stop()
            if isinstance(self.__conn_alive_event, asyncio.Event):
                self.__conn_alive_event.set()

    async def __callback(self, msg: ConsumerRecord):
        try:
            await self.__callbacks[msg.topic]().callback(msg)
        except Exception as exc:
            logger.exception(f"Kafka callback error {msg.topic}:{msg.value} - {exc.__class__.__name__}:{exc}")

    async def __start(self):
        if not self.__conn_stop_event.is_set():
            # __conn_stop_event没有被标记，说明任务还没有结束，无需重复启动
            logger.warning(f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> is already running, {self.__conn_alive_event}")
            return
        logger.success(f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> begin start ...")
        self.__conn_stop_event.clear()  # 清除标记，代表任务开始
        while self.conn_alive_flag:
            self.__conn_alive_event.clear()
            self.__conn_success_event.clear()
            await self.__init_consumer()

            # 创建新的Task监听的kafka消息，当这个监听任务结束时，会设置__conn_alive_event为关闭状态
            asyncio.create_task(self.__listening_consumer())

            await self.__conn_alive_event.wait()
            if isinstance(self.__consumer, AIOKafkaConsumer):
                logger.warning(f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> disconnected ... reconnect={self.conn_alive_flag}")
                client_ = self.__consumer
                self.__consumer = None
                await client_.stop()  # 此处等待资源释放

        self.__conn_stop_event.set()  # 标记任务结束
        self.__conn_success_event.set()
        self.__conn_alive_event.set()
        logger.warning(f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> client stopped")

    def __stop(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            self.__conn_success_event.clear()
        if isinstance(self.__conn_alive_event, asyncio.Event):
            self.__conn_alive_event.set()

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

    def restart(self):
        logger.warning(f"Call Restart {self}")
        self.__stop()

    def stop(self):
        self.conn_alive_flag = False
        logger.warning(f"Call Stop {self}")
        self.__stop()

    async def wait_connect(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            await self.__conn_success_event.wait()

    async def wait_stop(self):
        if isinstance(self.__conn_stop_event, asyncio.Event):
            await self.__conn_stop_event.wait()

    async def delete_topics(self, topics_name_set: Iterator[str]):
        if not isinstance(self.__consumer, AIOKafkaConsumer):
            logger.warning(f"Consumer not start, delete topics failed: {topics_name_set}")
            return

        success_, failed_ = await self._delete_topics(self.__consumer._client, topics_name_set)
        success_ and logger.warning(f"Delete Topics Success: {success_}")
        failed_ and logger.warning(f"Delete Topics Failed: {failed_}")

    async def get_topics(self) -> Set[str]:
        if not isinstance(self.__consumer, AIOKafkaConsumer):
            logger.warning("Consumer not start, get topics list failed")
            return set()
        return await self._get_topics(self.__consumer._client)

    async def create_topics(self, topic_config: List[Union[Dict, NewTopic]]):
        if not isinstance(self.__consumer, AIOKafkaConsumer):
            logger.warning(f"Consumer not start, create topics failed: {topic_config}")
            return
        config_ = [
            NewTopic(
                name=item_.get("name"),
                num_partitions=item_.get("num_partitions"),
                replication_factor=item_.get("replication_factor"),
                replica_assignments=item_.get("replica_assignments"),
                topic_configs=item_.get("topic_configs"),
            ) if isinstance(item_, dict) else item_
            for item_ in topic_config
            if isinstance(item_, NewTopic) or (isinstance(item_, dict) and item_.get("name") and item_.get("num_partitions"))
        ]
        success_, failed_ = await self._create_topics(self.__consumer._client, config_)
        success_ and logger.success(f"Create Topics Success: {success_}")
        failed_ and logger.warning(f"Create Topics Failed: {failed_}")


@dataclass
class KafkaProducerClient(CreateTopicMixin):
    """
    Kafka 生产者客户端
    - retry_interval : Producer 重连间隔 单位秒
    """
    bootstrap_servers: Set[str]
    user: str
    password: str
    retry_interval: int
    __pass_param: Dict

    conn_alive_flag: bool = False  # 保持连接的标记
    __conn_success_event: asyncio.Event = None  # 任务开始事件，防止重复启动
    __conn_alive_event: asyncio.Event = None  # 连接成功事件，标记连接任务已经成功连接到Kafka
    __conn_stop_event: asyncio.Event = None  # 任务结束事件

    def __init__(
        self,
        bootstrap_servers: Iterator[str],
        *,
        user: str = None,
        password: str = None,
        retry_interval: int = 10,
        **kwargs,
    ):
        super().__init__()
        self.bootstrap_servers = set(bootstrap_servers)
        self.user = user or None
        self.password = password or None
        self.retry_interval = retry_interval
        self.__pass_param = kwargs

        self.__producer: Optional[aiokafka.AIOKafkaProducer] = None

    def update_bootstrap_servers(self, new_bootstrap_servers: Iterator[str]):
        new_set_ = set(new_bootstrap_servers)
        if not new_set_ <= self.bootstrap_servers:
            self.restart()
        self.bootstrap_servers = new_set_
        return self

    async def __init_producer(self):
        self.__producer = None
        while self.conn_alive_flag:
            logger.info(
                f"Connect KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}>, _KafkaProducerClient__conn_success_event={self.__conn_success_event}"
            )
            try:
                producer_ = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    sasl_plain_username=self.user,
                    sasl_plain_password=self.password,
                    **self.__pass_param,
                )

                await producer_.start()
                self.__producer = producer_

                self.__conn_success_event.set()
                logger.success(
                    f"Successfully connect KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}>, _KafkaProducerClient__conn_success_event={self.__conn_success_event}"
                )
                break
            except Exception as exc:
                logger.warning(f"Failed to connect KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}> - {exc.__class__.__name__}:{exc}")
                await asyncio.sleep(self.retry_interval)

    async def __start(self):
        if not self.__conn_stop_event.is_set():
            # __conn_stop_event没有被标记，说明任务还没有结束，无需重复启动
            logger.warning(f"KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}> is already running, {self.__conn_alive_event}")
            return

        logger.success(f"KafkaConsumer<{self.user}:{self.password}@{self.bootstrap_servers}> begin start ...")
        self.__conn_stop_event.clear()  # 清除标记，代表任务开始
        while self.conn_alive_flag:
            self.__conn_alive_event.clear()
            self.__conn_success_event.clear()
            await self.__init_producer()

            # 等待__conn_alive_event被设置，说明连接关闭
            await self.__conn_alive_event.wait()
            if isinstance(self.__producer, AIOKafkaProducer):
                logger.warning(f"KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}> disconnected ... reconnect={self.conn_alive_flag}")
                client_ = self.__producer
                self.__producer = None
                await client_.stop()  # 此处等待资源释放

        self.__conn_stop_event.set()  # 标记任务结束
        self.__conn_success_event.set()
        self.__conn_alive_event.set()
        logger.warning(f"KafkaProducer<{self.user}:{self.password}@{self.bootstrap_servers}> client stopped")

    def __stop(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            self.__conn_success_event.clear()
        if isinstance(self.__conn_alive_event, asyncio.Event):
            self.__conn_alive_event.set()

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

    def restart(self):
        logger.warning(f"Call Restart {self}")
        self.__stop()

    def stop(self):
        self.conn_alive_flag = False
        logger.warning(f"Call Stop {self}")
        self.__stop()

    async def wait_connect(self):
        if isinstance(self.__conn_success_event, asyncio.Event):
            await self.__conn_success_event.wait()

    async def wait_stop(self):
        if isinstance(self.__conn_stop_event, asyncio.Event):
            await self.__conn_stop_event.wait()

    async def get_sender(self, topic: str) -> "KafkaProducerClient":
        if topic in self.exist_topics:
            return self
        # 先创建Topic
        conf_ = {
            topic: self.topics_conf.get(
                topic, NewTopic(
                    topic,
                    num_partitions=self.num_partitions,
                    replication_factor=self.replication_factor,
                    topic_configs=self.topic_configs
                )
            ),
        }
        if isinstance(self.__producer, AIOKafkaProducer):
            try:
                await self._auto_create_topics(
                    self.__producer.client,
                    conf_,
                )
            except Exception as exc:
                logger.error(f"Create Topic Error - {exc.__class__.__name__}:{exc}")

        return self

    async def delete_topics(self, topics_name_set: Iterator[str]):
        if not isinstance(self.__producer, AIOKafkaProducer):
            logger.warning(f"Producer not start, delete topics failed: {topics_name_set}")
        success_, failed_ = await self._delete_topics(self.__producer.client, topics_name_set)
        success_ and logger.warning(f"Delete Topics Success: {success_}")
        failed_ and logger.warning(f"Delete Topics Failed: {failed_}")

    async def get_topics(self) -> Set[str]:
        if not isinstance(self.__producer, AIOKafkaProducer):
            logger.warning("Producer not start, get topics list failed")
            return set()
        return await self._get_topics(self.__producer.client)

    async def create_topics(self, topic_config: List[Union[Dict, NewTopic]]):
        if not isinstance(self.__producer, AIOKafkaProducer):
            logger.warning(f"Producer not start, create topics failed: {topic_config}")
            return
        config_ = [
            NewTopic(
                name=item_.get("name"),
                num_partitions=item_.get("num_partitions"),
                replication_factor=item_.get("replication_factor"),
                replica_assignments=item_.get("replica_assignments"),
                topic_configs=item_.get("topic_configs"),
            ) if isinstance(item_, dict) else item_
            for item_ in topic_config
            if isinstance(item_, NewTopic) or (isinstance(item_, dict) and item_.get("name") and item_.get("num_partitions"))
        ]
        success_, failed_ = await self._create_topics(self.__producer.client, config_)
        success_ and logger.success(f"Create Topics Success: {success_}")
        failed_ and logger.warning(f"Create Topics Failed: {failed_}")

    def __enter__(self) -> AIOKafkaProducer:
        return self.__producer

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理Kafka连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if isinstance(exc_val, (KafkaConnectionError, KafkaTimeoutError)):
            logger.error(f"Kafka Error {exc_type}:{exc_val}")
            self.restart()
            return True

        if isinstance(exc_val, AssertionError):
            # Kafka客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"KafkaProducerClient:{self.__conn_success_event} -- {exc_type}:{exc_val}")
            return True

        return False

    async def __aenter__(self) -> AIOKafkaProducer:
        return self.__producer

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异常会传递进来，只处理Kafka连接错误的异常
        return True 时异常不会传递到使用的地方
        """
        if isinstance(exc_val, (KafkaConnectionError, KafkaTimeoutError)):
            logger.error(f"Kafka Error {exc_type}:{exc_val}")
            self.restart()
            return True

        if isinstance(exc_val, AssertionError):
            # Kafka客户端以及其他的断言错误，抛出AssertionError
            logger.warning(f"KafkaProducerClient:{self.__conn_success_event} -- {exc_type}:{exc_val}")
            return True

        return False
