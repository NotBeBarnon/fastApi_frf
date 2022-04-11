# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:16:52
# @Author  : fzx
# @Description :

from pydantic import Field, validator
from tortoise.contrib.pydantic import pydantic_model_creator

from .models import User

UserSchema = pydantic_model_creator(User, name="UserSchema", exclude=("password",))


class UserCreateSchema(pydantic_model_creator(User, name="UserCreateSchema", exclude=("uid",), exclude_readonly=True)):
    password_again: str = Field(..., description="重复输入验证密码")

    @validator("password_again")
    def password_again_validator(cls, password_again, values, **kwargs):
        if password_again != values["password"]:
            raise ValueError("两次密码不一致")
        return password_again

    class Config:
        title = "UserCreateSchema"


class UserUpdateSchema(pydantic_model_creator(User, name="UserUpdateSchema", exclude=("uid",), exclude_readonly=True)):
    username: str = None
    # name: Optional[str] = Field(None, description="用户名字")
    # family_name: Optional[str] = Field(None, description="用户姓")
    password: str = None
    password_again: str = Field(None, description="再次验证密码")

    @validator("password")
    def password_validator(cls, password, values, **kwargs):
        if not password:
            raise ValueError("密码不可设置为空")
        return password

    @validator("password_again", always=True)
    def password_again_validator(cls, password_again, values, **kwargs):
        if "password" in values and password_again != values["password"]:
            raise ValueError("密码不一致")
        return password_again

    class Config:
        title = "UserUpdateSchema"
