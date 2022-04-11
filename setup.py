# -*- coding: utf-8 -*-
# @Time    : 2022/3/2
# @Author  : fzx
# @Description :
import platform
import re
import sys
from pathlib import Path
from typing import List, Iterator

from cx_Freeze import setup, Executable

from src.version import VERSION

PROJECT_DIR: Path = Path(__file__).parent


# 三个读取依赖的工具方法
def get_python_packages(file_path: Path) -> Iterator[str]:
    """
    查找目录下所有python包
    """
    if not file_path.is_dir():
        return
    for child in file_path.iterdir():
        if child.is_dir():
            is_python_package = set(child.glob("__init__.py"))
            if is_python_package:
                # print(f"init-{is_python_package}")
                yield child.name


def get_all_packages() -> Iterator[str]:
    """
    获取site中所有的python包
    """
    site_regex = re.compile("[\\\\|/]site-packages")
    site_path = None
    for path in sys.path:
        if site_regex.search(path):
            site_path = Path(path)
    if site_path:
        yield from get_python_packages(site_path)


def get_all_requirements() -> Iterator[str]:
    package_regex = re.compile("[a-zA-Z\-_]+")

    for line_content in open(PROJECT_DIR / "requirements.txt", "r"):
        pack_name = package_regex.match(line_content)
        if pack_name:
            yield pack_name.group().replace("-", "_")


# 添加依赖
packages: List = []
if platform.system() == "Linux":
    packages.append("uvloop")

requirements_str = "-".join(get_all_requirements())
for pack in get_all_packages():
    if pack in requirements_str:
        packages.append(pack)

build_exe_options = {
    "include_files": ["project_env", "pyproject.toml"],
    "packages": packages,
    "excludes": [],
}

setup(
    name="FastSample",
    version=VERSION,
    description="FastAPI Sample",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py")],
)
