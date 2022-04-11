# -*- coding: utf-8 -*-
# @Time    : 2022/3/3 14:37
# @Author  : fzx
# @Description :
import hashlib


def make_password(password: str):
    return hashlib.md5(password.encode(encoding="ascii")).hexdigest()


if __name__ == '__main__':
    pass
