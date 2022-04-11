# -*- coding: utf-8 -*-
# @Time    : 2022/3/7:11:23
# @Author  : fzx
# @Description : emqx连接（后续补上）
import os
import gmqtt
from typing import List
import asyncio
client_id = f"MQTT_{os.urandom(8).hex()}"
gmqClient = gmqtt.Client(client_id)


class GMQTT:

    def __init__(self, topics: List[str], on_message, loop_=None):

        self.mqtt_ip = "127.0.0.1"
        self.mqtt_port = "1234"
        self.topics = topics

        self._loop = loop_ if loop_ else asyncio.get_event_loop()

        self.gmqClient = gmqClient
