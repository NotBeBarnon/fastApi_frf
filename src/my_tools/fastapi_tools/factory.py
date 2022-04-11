# -*- coding: utf-8 -*-
# @Time    : 2022/12/16 9:14
# @Author  : fzx
# @Description :
from typing import List, Type

from tortoise import Model
from tortoise.contrib.fastapi import HTTPNotFoundError
from tortoise.contrib.pydantic import PydanticModel

from .decorators import Action


def generate_all(model: Model, schema: Type[PydanticModel]):
    """
    生成视图集的all方法
    Args:
        model: 视图集的orm模型
        schema: 视图输出的序列化

    Returns:
        CoroutineType: 由 async def 创建的协程方法
    """

    @Action.get(f"/{model.__name__.lower()}s", response_model=List[schema])
    async def all(self):
        return await schema.from_queryset(model.all())

    all.__doc__ = f"Query all {model.__name__}"

    return all


def generate_create(model: Model, schema: Type[PydanticModel], input_schema: PydanticModel):
    """
    生成视图集的create方法
    Args:
        model: 视图集的orm模型
        schema: 视图输出序列化
        input_schema: http视图输入的body序列化对象

    Returns:
        CoroutineType: 由 async def 创建的协程方法
    """

    @Action.post(f"/{model.__name__.lower()}", response_model=schema)
    async def create(self, body: input_schema):
        return await schema.from_tortoise_orm(await model.create(**body.dict()))

    create.__doc__ = f"Create {model.__name__}"
    return create


def generate_get(model: Model, schema: Type[PydanticModel], pk_type: Type):
    """
    生成视图集的get方法
    Args:
        model: 视图集的orm模型
        schema: 视图输出序列化
        pk_type: 主键类型

    Returns:
        CoroutineType: 由 async def 创建的协程方法
    """

    @Action.get(f"/{model.__name__.lower()}/{{pk}}", response_model=schema, responses={404: {"model": HTTPNotFoundError}})
    async def get(self, pk: pk_type):
        return await schema.from_queryset_single(model.get(pk=pk))

    get.__doc__ = f"Get {model.__name__} by primary key"

    return get


def generate_update(model: Model, schema: Type[PydanticModel], pk_type: Type, input_schema: PydanticModel):
    """
    生成视图集的update方法
    Args:
        model: 视图集的orm模型
        schema: 视图输出序列化
        pk_type: 主键类型
        input_schema: http视图的body序列化

    Returns:
        CoroutineType: 由 async def 创建的协程方法
    """

    @Action.patch(f"/{model.__name__.lower()}/{{pk}}", response_model=schema, responses={404: {"model": HTTPNotFoundError}})
    async def update(self, pk: pk_type, body: input_schema):
        await model.filter(pk=pk).update(**body.dict(exclude_unset=True, exclude_defaults=True))
        return await schema.from_queryset_single(model.get(pk=pk))

    update.__doc__ = f"Update {model.__name__} by primary key"

    return update


def generate_delete(model: Model, schema: Type[PydanticModel], pk_type: Type):
    """
    生成视图集的delete方法
    Args:
        model: 视图集的orm模型
        schema: 视图输出序列化
        pk_type: 主键类型

    Returns:
        CoroutineType: 由 async def 创建的协程方法
    """

    @Action.delete(f"/{model.__name__.lower()}/{{pk}}", response_model=schema, responses={404: {"model": HTTPNotFoundError}})
    async def delete(self, pk: pk_type):
        obj = await model.get(pk=pk)
        deleted_count_ = await model.filter(pk=pk).delete()
        return await schema.from_tortoise_orm(obj)

    delete.__doc__ = f"Delete {model.__name__} by primary key"

    return delete
