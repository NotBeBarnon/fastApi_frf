# -*- coding: utf-8 -*-
# @Time    : 2022/3/3 11:00
# @Author  : fzx
# @Description : 暂未实现

from random import choice
from typing import Any, Optional

import arrow
from tortoise import ConfigurationError, ModelMeta
from tortoise.fields import Field
from tortoise.validators import MaxLengthValidator

NUMBER_SEQUENCE = "0123456789"


def build_short_uid_pre():
    return arrow.now().format("YYMM")


def build_short_uid(*args, **kwargs):
    """生成短uid"""
    suf_ = "".join([choice(NUMBER_SEQUENCE) for _ in range(5)])
    return f"{build_short_uid_pre()}{suf_}"


class ShortUIDField(Field, str):
    """
    自定义的短uuid字段
    """

    def __init__(self, max_length: int, **kwargs: Any) -> None:
        if int(max_length) < 1:
            raise ConfigurationError("'max_length' must be >= 1")
        # 添加前缀计数器
        self.PRE_COUNT = {
            "pre": "0000",
            "count": 1
        }

        self.max_length = int(max_length)
        super().__init__(**kwargs)
        self.validators.append(MaxLengthValidator(self.max_length))

    def to_db_value(self, value: Any, instance: "Union[Type[Model], Model]") -> Optional[str]:
        if isinstance(instance, ModelMeta):
            return value and str(value)

        # 自定义个uid规则
        if not value:
            pre_ = build_short_uid_pre()
            if self.PRE_COUNT["pre"] == pre_:
                suf_ = self.PRE_COUNT["count"] + 1
            else:
                # 重置计数器
                self.PRE_COUNT = {
                    "pre": "0000",
                    "count": 1
                }
                suf_ = 1
            value = f"{pre_}{suf_:05d}"
        return value and str(value)

    @property
    def constraints(self) -> dict:
        return {
            "max_length": self.max_length,
        }

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"CHAR({self.max_length})"
