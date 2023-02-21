# -*- coding: utf-8 -*-
# @Time    : 2022/12/7 9:17
# @Author  : fzx
# @Description : 单例工具
import abc
from typing import Any


class SingletonDecorator(object):
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self) -> Any:
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls()
        return self._instance[self._cls]


class SingletonMeta(type):
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls.__instances[cls]


class SingletonABCMeta(abc.ABCMeta, SingletonMeta):
    pass
