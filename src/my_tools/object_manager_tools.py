# -*- coding: utf-8 -*-
# @Time    : 2023/2/17:15:19
# @Author  : fzx
# @Description : 公共

from typing import Any

from src.my_tools.singleton_tools import SingletonMeta

__all__ = (
    "ObjectManager",
    "global_om",
)


class ObjectManager(dict, metaclass=SingletonMeta):

    def register(self, key: Any, value: Any):
        if key in self:
            raise KeyError("key already exists")
        self[key] = value

    def __call__(self, obj_key, **kwargs):
        return self[obj_key](**kwargs)


global_om = ObjectManager()
