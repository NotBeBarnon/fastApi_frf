# -*- coding: utf-8 -*-
# @Time    : 2022/4/2:17:26
# @Author  : fzx
# @Description :



import socket

from bsonrpc import JSONRpc



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 6000))

rpc = JSONRpc(s)
server = rpc.get_peer_proxy()

result = server.swapper("hahahhahahaha")

print(result)
rpc.close()