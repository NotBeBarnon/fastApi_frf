# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:17:48
# @Author  : fzx
# @Description :
import arrow
from dns.enum import IntEnum
from tortoise import models, fields

from src.settings import LOCAL_TIMEZONE
from . import app_name

class BeamTypeEnum(IntEnum):
    ka = 1
    x = 2

class Beam(models.Model):
    """波束"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, null=False)
    type = fields.IntEnumField(BeamTypeEnum, null=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    def created_time(self) -> str:
        """
        Returns the created_time
        """
        return arrow.get(self.created_at).to(LOCAL_TIMEZONE).format("YYYY-MM-DD HH:mm:ss")

    class PydanticMeta:
        computed = ["created_time"]
        exclude = []

    class Meta:
        table = f"{app_name}_beam"