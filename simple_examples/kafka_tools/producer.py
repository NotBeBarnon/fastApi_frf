# -*- coding: utf-8 -*-
# @Time    : 2022/4/23 0:14
# @Author  : Tuffy
# @Description :
import asyncio

import orjson
from loguru import logger

from src.my_tools.kafka_tools.clients import KafkaProducerClient, TopicConfig


async def main():
    pc_ = KafkaProducerClient(["10.64.5.70:30093"])
    pc_.start()
    await pc_.wait_connect()
    with (await pc_.get_sender("RCST_STATE_CHANGED")) as p_:
        fut_ = await p_.send(
            "RCST_STATE_CHANGED",
            orjson.dumps(
                {"msg": "<RCST-{device}> offline", "type": "RCST_OFFLINE", "rcst_hid": "00-0a-35-00-01-ac", "interactive_network_id": 1, "device": 210172}
            ),
            key=b"DEVICE"
        )
        await fut_
        # await asyncio.sleep(10)
        # fut_ = await p_.send(
        #     "RCST_STATE_CHANGED",
        #     orjson.dumps(
        #         {
        #             "msg": "<RCST-{device}> logon success",
        #             "type": "RCST_LOGON_SUCCESS",
        #             "rcst_hid": "aa-bb-cc-dd-ee-11",
        #             "device": 2004
        #         }
        #     ),
        #     key=b"DEVICE"
        # )
        # await fut_
        # await asyncio.sleep(10)
        # fut_ = await p_.send(
        #     "RCST_STATE_CHANGED",
        #     orjson.dumps(
        #         {
        #             "msg": "<RCST-{device}> offline",
        #             "type": "RCST_OFFLINE",
        #             "rcst_hid": "aa-bb-cc-dd-ee-11",
        #             "device": 2004
        #         }
        #     ),
        #     key=b"DEVICE"
        # )
        # await fut_
    pc_.stop()
    await pc_.wait_stop()


async def producer_manage_topics():
    pc_ = KafkaProducerClient(["10.64.5.70:30093"])
    pc_.start()
    await pc_.wait_connect()
    logger.info("ProducerClient connect success")

    with (await pc_.get_sender("AAFSTest")) as p_:
        for _ in range(2):
            fut_ = await p_.send("AAFSTest", b"hello world")
            await fut_
            logger.success(f"Send msg success - {p_}")
            await asyncio.sleep(1)

    await pc_.create_topics(
        [
            {
                "name": "AAAAAAAAAAA",
                "num_partitions": 1,
                "replication_factor": 3,
            },
            TopicConfig(
                name="AAAAAAAAAAB",
                num_partitions=1,
                replication_factor=3,
            )
        ]
    )
    topics_ = await pc_.get_topics()
    logger.success(f"All Topics: {topics_}")
    await pc_.delete_topics(["AAAAAAAAAAA", "AAAAAAAAAAB"])

    pc_.stop()
    await pc_.wait_stop()


if __name__ == '__main__':
    asyncio.run(main())
