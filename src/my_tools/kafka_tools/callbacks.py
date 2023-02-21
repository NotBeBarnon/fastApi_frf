# -*- coding: utf-8 -*-
# @Time    : 2022/3/14 16:40
# @Author  : Tuffy
# @Description :
import abc
from dataclasses import dataclass

from aiokafka import ConsumerRecord

from src.my_tools.singleton_tools import SingletonABCMeta

__all__ = (
    "BaseTopicCall",
    "BaseTopicCallSingle",
)


@dataclass
class BaseTopicCall(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def topic(self) -> str:
        ...

    @abc.abstractmethod
    async def callback(self, msg: ConsumerRecord):
        ...
        # ConsumerRecord(
        #     topic='AAFSTest',
        #     partition=0,
        #     offset=34,
        #     timestamp=1659606624645,
        #     timestamp_type=0,
        #     key=b'\x01',
        #     value=b'hello world',
        #     checksum=None,
        #     serialized_key_size=1,
        #     serialized_value_size=11,
        #     headers=()
        # )


class BaseTopicCallSingle(BaseTopicCall, metaclass=SingletonABCMeta):

    @abc.abstractmethod
    async def callback(self, msg: ConsumerRecord):
        ...

    @property
    @abc.abstractmethod
    def topic(self):
        ...
