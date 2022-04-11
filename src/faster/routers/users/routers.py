# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:16:52
# @Author  : fzx
# @Description :


from fastapi import APIRouter, Depends

user_router = APIRouter(prefix="/user", dependencies=[Depends()])