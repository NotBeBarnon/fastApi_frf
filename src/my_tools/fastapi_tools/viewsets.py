# -*- coding: utf-8 -*-
# @Time    : 2022/3/29 11:19
# @Author  : fzx
# @Description :
import logging
from functools import wraps
from types import MethodType
from typing import Optional, Generator, Callable, Tuple, Dict, List, Any

from fastapi import APIRouter, Response
from fastapi.types import DecoratedCallable
from tortoise import Model
from tortoise.contrib.pydantic import PydanticModel

from .factory import generate_all, generate_create, generate_get, generate_update, generate_delete

logger = logging.getLogger("fastapi")


class CBVTransponder(object):
    pass


class ViewSetMetaClass(type):
    _essential_attribute_sets = {"model", "schema", "pk_type", "views"}
    _all_view_name = {"all", "get", "create", "update", "delete"}
    _inputable_view_name = {"create", "update"}

    def __new__(mcs, name, bases, attrs):
        if name == "BaseViewSet":
            return super().__new__(mcs, name, bases, attrs)

        # 检查是否包含生成基础的方法所需的属性
        if not mcs._check_attrs(attrs, name):
            return super().__new__(mcs, name, bases, attrs)
        # 生成基础方法
        if "all" in attrs["views"] and "all" not in attrs:
            attrs["all"] = generate_all(attrs["model"], attrs["schema"])

        if "create" in attrs["views"] and "create" not in attrs:
            attrs["create"] = generate_create(attrs["model"], attrs["schema"], attrs["views"]["create"])

        if "get" in attrs["views"] and "get" not in attrs:
            attrs["get"] = generate_get(attrs["model"], attrs["schema"], attrs["pk_type"])

        if "update" in attrs["views"] and "update" not in attrs:
            attrs["update"] = generate_update(attrs["model"], attrs["schema"], attrs["pk_type"], attrs["views"]["update"])

        if "delete" in attrs["views"] and "delete" not in attrs:
            attrs["delete"] = generate_delete(attrs["model"], attrs["schema"], attrs["pk_type"])

        return super().__new__(mcs, name, bases, attrs)

    def __call__(cls, *args, **kwargs):
        # _instance = super().__call__(*args, **kwargs)
        return super().__call__(*args, **kwargs)

    @staticmethod
    def _check_attrs(attrs: Dict, name: str):
        """
        检查属性合法性
        Args:
            attrs: 所有的类属性
            name: 类名称

        Returns:
            bool: True 合法； False 不合法
        """
        if not all((key in attrs for key in ViewSetMetaClass._essential_attribute_sets)):
            logger.warning(f"Class<{name}> lacks {ViewSetMetaClass._essential_attribute_sets}.")
            return False
        if not issubclass(attrs["model"], Model):
            logger.warning(f"The \"model\" in {name} is invalid.")
            return False
        if not issubclass(attrs["schema"], PydanticModel):
            logger.warning(f"The \"schema\" in {name} is invalid.")
            return False
        if not isinstance(attrs["pk_type"], type):
            logger.warning(f"The \"pk_type\" in {name} is invalid.")
            return False

        return ViewSetMetaClass._check_views(attrs["views"], name)

    @staticmethod
    def _check_views(views: Any, name: str) -> bool:
        """
        检查视图集配置的views是否合法
        Args:
            views: 基础视图配置
            name: 类名称

        Returns:
            bool: True 合法；False 不合法
        """
        if not isinstance(views, dict):
            logger.warning(f"The \"views\" in {name} is invalid.")
            return False
        for key, val in views.items():
            if key in ViewSetMetaClass._inputable_view_name:
                if not issubclass(val, PydanticModel):
                    logger.warning(f"The \"views\" in {name} is invalid.")
                    return False

        return True


class BaseViewSet(metaclass=ViewSetMetaClass):
    __transponder: Optional[CBVTransponder] = None

    @classmethod
    def __get_views(cls) -> Generator[Tuple[str, DecoratedCallable], None, None]:
        for attr_name in dir(cls):
            view = getattr(cls, attr_name)
            if hasattr(view, "__fast_view__"):
                yield attr_name, view

    @classmethod
    def register(cls, router: APIRouter):
        if cls.__transponder is not None:
            return
        # 实例化视图函数转发器
        cls.__transponder = CBVTransponder()
        for view_name, view_func in cls.__get_views():
            # 创建视图函数
            fast_route = cls.__create_fast_route(view_func, view_name, cls)
            # 转发器动态添加视图函数路由
            setattr(cls.__transponder, view_name, MethodType(fast_route, cls.__transponder))
            # 注册视图函数
            router.api_route(**cls.__build_fast_view_params(view_func.__fast_view__, view_func))(getattr(cls.__transponder, view_name))

    @classmethod
    def __build_fast_view_params(cls, fast_view: Dict, view_func: DecoratedCallable) -> Dict:
        if fast_view["summary"] is None:
            fast_view["summary"] = view_func.__name__.replace("_", " ").strip().title()
        if fast_view["tags"] is None:
            fast_view["tags"] = [cls.__name__]
        elif isinstance(fast_view["tags"], List):
            fast_view["tags"].append(cls.__name__)
        return fast_view

    @staticmethod
    def __create_fast_route(view_func: DecoratedCallable, view_name: str, call_cls: Callable) -> DecoratedCallable:
        @wraps(view_func)
        async def fast_route(self_, *view_args, **view_kwargs) -> Response:
            return await getattr(call_cls(), view_name)(*view_args, **view_kwargs)

        return fast_route
