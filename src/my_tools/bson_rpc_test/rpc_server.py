# -*- coding: utf-8 -*-
# @Time    : 2022/4/2:17:17
# @Author  : fzx
# @Description :
import socket

from bsonrpc import JSONRpc
from bsonrpc import service_class, request


@service_class
class ServerServices(object):

    @request
    def swapper(self, txt):
        return "".join(reversed(list(txt)))


ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ss.bind(("localhost", 6000))
ss.listen(10)


while True:
    s, _ = ss.accept()
    JSONRpc(s, ServerServices())

