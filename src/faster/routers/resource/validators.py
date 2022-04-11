# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:17:48
# @Author  : fzx
# @Description :
from typing import Any

from tortoise.exceptions import ValidationError
from tortoise.validators import Validator


class OtherValidator(Validator):
    """自定义验证器"""

    def __init__(self, num: Any):
        self.num = num

    def __call__(self, value: Any):
        raise ValidationError(f"Server Port cannot be {self.num}")
