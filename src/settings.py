# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:14:09
# @Author  : fzx
# @Description : 配置文件

import io
import json
import os
import sys
from pathlib import Path

import dotenv
import tomlkit
from loguru import logger

# 项目根目录
PROJECT_DIR: Path = Path(__file__).parents[1]
if PROJECT_DIR.name == "lib":  # 适配cx_Freeze打包项目后根目录的变化
    PROJECT_DIR = PROJECT_DIR.parent

# 加载环境变量
dotenv.load_dotenv(PROJECT_DIR.joinpath("project_env"))
# 加载项目配置
__toml_config = json.loads(
    json.dumps(
        tomlkit.loads(PROJECT_DIR.joinpath("pyproject.toml").read_bytes())
    )
)  # 转换包装类型为Python默认类型
VERSION = __toml_config["tool"]["commitizen"]["version"]
VERSION_FORMAT = __toml_config["tool"]["commitizen"]["tag_format"].replace("$version", VERSION)
PROJECT_CONFIG = __toml_config["myproject"]


# DEBUG控制
DEV = True if PROJECT_CONFIG.get("DEV", False) else False
# 生产环境控制
PROD = False if DEV or not PROJECT_CONFIG.get("PROD", True) else True

DEV and logger.info("[DEV] Server")
PROD and logger.info("[PROD] Server")

# 服务监听
HTTP_API_LISTEN_HOST = PROJECT_CONFIG.get("HTTP_API_LISTEN_HOST", "0.0.0.0")
HTTP_API_LISTEN_PORT = int(os.getenv("HTTP_API_LISTEN_PORT", 8080))
HTTP_BASE_URL = PROJECT_CONFIG.get("HTTP_BASE_URL", "/api/sample")

# 消息队列配置
MQ_CONFIG = PROJECT_CONFIG["mq"]
__kafka_service = os.getenv("FS_KAFKA_SERVICE")
if __kafka_service:
    MQ_CONFIG["bootstrap_servers"] = [item_.strip() for item_ in __kafka_service.split(",")]


# redis 配置
REDIS_CONFIG = PROJECT_CONFIG["redis"]
__redis_service = os.getenv("FS_REDIS_SENTINEL_SERVICE")
__redis_service = [(item_[0].strip(), int(item_[1])) for item_ in REDIS_CONFIG["sentinels"]["service"]] \
    if __redis_service is None \
    else [(item_[0].strip(), int(item_[1])) for item_ in (_.split(":") for _ in __redis_service.split(","))]
REDIS_CONFIG.update(
    {
        "host": os.getenv("FS_REDIS_HOST", REDIS_CONFIG["host"]),
        "port": int(os.getenv("FS_REDIS_PORT", REDIS_CONFIG["port"])),
        "sentinels": {
            "service": __redis_service,
            "service_name": os.getenv("FS_REDIS_SENTINEL_SERVICE_NAME", REDIS_CONFIG["sentinels"]["service_name"]),
        }
    }
)

# 配置日志
LOGGER_CONFIG = {
    "handlers": [
        {
            "sink": sys.stdout,
            "level": "DEBUG" if DEV else PROJECT_CONFIG.get("LOG_LEVEL", "info").upper(),
            "enqueue": True,
            "backtrace": True,
            "diagnose": True,
            "catch": True
        },
        {
            "sink": PROJECT_DIR.joinpath("logs/project.log"),
            "rotation": "3 MB",
            "retention": "30 days",
            "level": "INFO",
            "enqueue": True,
            "backtrace": True,
            "diagnose": True,
            "encoding": "utf-8",
            "catch": True
        },
    ]
}

logger.configure(**LOGGER_CONFIG)

DEFAULT_TIMEZONE = "UTC"
LOCAL_TIMEZONE = "Asia/Shanghai"

DATABASE_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": os.getenv("FASTSAMPLE_DATABASE_HOST", "localhost"),
                "port": int(os.getenv("FASTSAMPLE_DATABASE_PORT", 3306)),
                "user": os.getenv("FASTSAMPLE_DATABASE_USER", "root"),
                "password": os.getenv("FASTSAMPLE_DATABASE_PASSWORD", "123456"),
                "database": os.getenv("FASTSAMPLE_DATABASE_NAME", "FastSample"),
                "minsize": PROJECT_CONFIG.get("database", {}).get("minsize", 24),
                "maxsize": PROJECT_CONFIG.get("database", {}).get("maxsize", 24),
                "charset": "utf8mb4",
                "pool_recycle": 3600
            }
        },
        # "double": {
        #     "engine": "tortoise.backends.mysql",
        #     "credentials": {
        #         "host": os.getenv("FASTDOUBLE_DATABASE_HOST", "localhost"),
        #         "port": int(os.getenv("FASTDOUBLE_DATABASE_PORT", 3306)),
        #         "user": os.getenv("FASTDOUBLE_DATABASE_USER", "fzx"),
        #         "password": os.getenv("FASTDOUBLE_DATABASE_PASSWORD", "satncs"),
        #         "database": os.getenv("FASTDOUBLE_DATABASE_NAME", "FastDouble"),
        #         "charset": "utf8mb4",
        #     }
        # },
    },
    "apps": {
        # 1.注意此处的app代表的并不与FastAPI的routers对应
        # 2.在Tortoise-orm使用外键时，需要用到该app名称来指执行模型，"app.model"，所以同一个app中不要出现名称相同的两个模型类
        # 3.app的划分结合 规则2与实际情况进行划分即可
        # "user": {
        #     "models": [
        #         "src.faster.routers.user.models",
        #     ],
        #     "default_connection": "default",
        # },
        # "double": {
        #     "models": [
        #         "src.faster.routers.resource.models",
        #     ],
        #     "default_connection": "double",
        # }
    },
    "use_tz": True,  # 设置数据库总是存储utc时间
    "timezone": DEFAULT_TIMEZONE,  # 设置时区转换，即从数据库取出utc时间后会被转换为timezone所指定的时区时间（待验证）
}
# 仅开发时需要记录迁移情况
DEV and DATABASE_CONFIG["apps"].update({
    "aerich": {
        "models": ["aerich.models"],
        "default_connection": "default",
    }})
