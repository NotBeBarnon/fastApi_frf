# -*- coding: utf-8 -*-
# @Time    : 2022/4/21 20:23
# @Author  : Tuffy
# @Description :
import asyncio

from aiokafka import ConsumerRecord
from loguru import logger

from src.my_tools.kafka_tools.callbacks import BaseTopicCall
from src.my_tools.kafka_tools.clients import KafkaConsumerClient, TopicConfig


class NCCFastSampleTestTopicCall(BaseTopicCall):
    """
    声明固定topic的回调函数
    """
    topic = "NCC_FORWARD_BROADCAST"

    async def callback(self, msg: ConsumerRecord):
        logger.debug(f"Recv [{msg.topic} - {msg.key} ]msg: {msg.value}")


class RCSTFastSampleTestTopicCall(BaseTopicCall):
    """
    声明固定topic的回调函数
    """
    topic = "RCST_REVERSE_UNICAST"

    async def callback(self, msg: ConsumerRecord):
        logger.debug(f"Recv [{msg.topic} - {msg.key} ]msg: {msg.value}")


async def main():
    cc_ = KafkaConsumerClient(["124.223.5.168:9092"], group="FSTEST")
    cc_.register_callbacks([NCCFastSampleTestTopicCall])
    cc_.start()

    await cc_.wait_connect()
    logger.info("Consumer connect success")
    await asyncio.sleep(100)
    await cc_.wait_stop()
    cc_.stop()


async def consumer_manage_topics():
    cc_ = KafkaConsumerClient(["10.64.5.70:30093"])
    cc_.register_callbacks([])
    cc_.start()

    await cc_.wait_connect()
    logger.info("Consumer connect success")

    await cc_.create_topics(
        [
            {
                "name": "AAAAAAAAAAA",
                "num_partitions": 1,
                "replication_factor": 2,
            },
            TopicConfig(
                name="AAAAAAAAAAB",
                num_partitions=1,
                replication_factor=2,
            )
        ]
    )
    topics_ = await cc_.get_topics()
    logger.success(f"All Topics: {topics_}")
    await cc_.delete_topics(["AAAAAAAAAAA", "AAAAAAAAAAB"])

    cc_.stop()
    await cc_.wait_stop()


if __name__ == '__main__':
    asyncio.run(main())
