# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:17:48
# @Author  : fzx
# @Description :
from tortoise.contrib.pydantic import pydantic_model_creator

from .models import Beam, BeamTypeEnum

BeamSchema = pydantic_model_creator(Beam, name="BeamSchema")
BeamCreateSchema = pydantic_model_creator(Beam, name="BeamCreateSchema", exclude=("id",), exclude_readonly=True)


class BeamUpdateSchema(pydantic_model_creator(Beam, name="BeamUpdateSchema", exclude=("id",), exclude_readonly=True)):
    name: str = None
    type: BeamTypeEnum = None

    class Config:
        title = "BeamUpdateSchema"
