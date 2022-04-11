# -*- coding: utf-8 -*-
# @Time    : 2022/12/14 14:53
# @Author  : fzx
# @Description :  Tortoise字段验证器
from typing import Union, List

from tortoise.exceptions import ValidationError
from tortoise.validators import Validator


class MaxValidator(Validator):
    """最大值验证器"""

    def __init__(self, num: int):
        self.num = num

    def __call__(self, value: int):
        if value > self.num:
            raise ValidationError(f"Value '{value}' exceeds the maximum {self.num}")


class MinValidator(Validator):
    """最小值验证器"""

    def __init__(self, num: int):
        self.num = num

    def __call__(self, value: int):
        if value < self.num:
            raise ValidationError(f"Value '{value}' exceeds the minimum {self.num}")


class NotValidator(Validator):
    """非值验证器"""

    def __init__(self, values: List[Union[str, int]]):
        self.values = values

    def __call__(self, value: Union[str, int]):
        if value in self.values:
            raise ValidationError(f"Value '{value}' cannot be in {self.values}")


class InValidator(Validator):
    """取值验证器"""

    def __init__(self, values: List[Union[str, int]]):
        self.values = values

    def __call__(self, value: Union[str, int]):
        if value not in self.values:
            raise ValidationError(f"Value '{value}' must be in {self.values}")
