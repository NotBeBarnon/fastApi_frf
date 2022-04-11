# FastAPI示例框架

## 1 项目结构

本项目目录结构如下，其中`*`标为目录，以下出现的目录为项目必须文件，不允许添加git忽略：

```
├── main.py
├── setup.py
├── migrations *
├── project_env
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── .dockerignore
├── docker *
│   ├── build_dockerfile
│   └── python_dockerfile
├── documents *
│   └── dev.md
└── src *
```

### 1.1 项目依赖文件

- project_env：环境变量文件，启动时从该文件中加载环境变量。
- pyproject.toml：项目配置文件，包括一些开发依赖包Commitizen和Aerich的配置也包括在内。
- requirements.txt：python的依赖文件，记录安装的包。
- docker：此目录包含docker打包镜像时使用的配置文件。
  - build_dockerfile：打包cx_Freeze编译结果为docker镜像的配置文件。
  - python_dockerfile：打包项目python源码为docker镜像的配置文件。
- .dockerignore: docker忽略的配置文件。
- .gitignore: git忽略的配置文件。

### 1.2 项目启动文件

- main.py: 程序入口文件，从`src`目录中导入`Application`。
- setup.py: cx_Freeze编译的脚本文件，使用`python setup.py build`调用编译程序，编译结果会生成在`./build`目录中。

### 1.3 忽略目录

除了项目的基本结构外，在项目运行或编译过程中还会产生一些其他目录，这些目录**应该**被git忽略，结构如下：

```
...
├── build *
├── logs *
...
```

- build: 编译结果目录，git应该忽略，但是使用build_dockerfile文件进行docker镜像的打包时，改目录**不应该**被`.dockerignore`文件忽略。
- logs: 运行日志文件目录，git和docker都应该忽略。

### 1.4 源码目录

项目开发源码在`src`目录下，其目录结构如下：

```
└── src *
    ├── __init__.py
    ├── application.py
    ├── settings.py
    ├── version.py
    ├── faster *
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── events.py
    │   ├── exceptions.py
    │   ├── middlewares.py
    │   └── routers *
    ├── my_tools *
    │   ├── __init__.py
    │   ├── password_tools.py
    │   ├── regex_tools.py
    │   ├── singleton_tools.py
    │   ├── fastapi_tools *
    │   └── tortoise_tools *
    └── my_apps *
```

- application.py: Typer的终端应用程序文件，用于启动FastAPI的服务。

- settings.py: 项目运行的配置文件。

- faster: FastAPI项目目录。

  - apps.py: FastAPI的实例文件。
  - events.py: FastAPI的startup与shutdown事件回调函数文件。
  - exceptions.py: FastAPI的异常回调函数文件。
  - middlewares.py: FastAPI的中间件文件。
  - routers: FastAPI所有的子路由目录
    - models.py: 数据库的orm模型文件。
    - routers.py: 视图函数文件。
    - schemas.py: 视图函数接收和响应数据的序列化schema类文件。
    - validators: 数据库orm模型字段的验证器文件。

- my_tools: 工具包目录

  - singleton_tools.py: 单例模式工具
  - fastapi_tools: FastAPI的CBV工具
  - tortoise_tools: Tortoise一些扩展工具

- my_apps：其他服务

  

## 2 数据库迁移

数据库迁移使用到`requirements.txt -> DEV Depend -> Database migration`中的`aerich`库，在开发中需要使用`pip install aerich`命令进行安装。

### 2.1 模型设置

首先确定好`settings.py`中关于`Tortoise-orm`的数据库设置变量是否正确，并确认变量名称，本例中的名称为`DATABASE_CONFIG`。

值得注意的是，在数据库设置的`models`中必须添加`aerich.models`，它是用来记录`aerich`的迁移记录的，并且只需要在默认的`default`数据库中添加即可。所以修改后的`DATABASE_CONFIG`如下：

```python
DEFAULT_TIMEZONE = "UTC"
LOCAL_TIMEZONE = "Asia/Shanghai"

DATABASE_CONFIG = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": "localhost",
                "port": 3306,
                "user": "user",
                "password": "password",
                "database": "Database name",
                "charset": "utf8mb4",
            }
        },
        "double": {
            ...
        },
    },
    "apps": {
        # 1.注意此处的app代表的并不与FastAPI的routers对应
        # 2.在Tortoise-orm使用外键时，需要用到该app名称来指执行模型，"app.model"，所以同一个app中不要出现名称相同的两个模型类
        # 3.app的划分结合 规则2与实际情况进行划分即可
        "TortoiseAppUser": {
            "models": [
                "src.faster.routers.user.models", # 指定该App中所有的模型
            ],
            "default_connection": "default", # 指定所使用的 "connections" 字段中的数据库连接
        },
        "TortoiseAppDouble": {
            ...
        }
    },
    "use_tz": True,  # 设置数据库总是存储utc时间
    "timezone": DEFAULT_TIMEZONE,  # 设置默认时区
}
# 下列配置用于指定aerich迁移配置，仅开发时需要记录迁移情况
DEV and DATABASE_CONFIG["apps"].update({
    "aerich": {
        "models": ["aerich.models"],
        "default_connection": "default",
    }})
```

### 2.2 初始化

激活Python环境并安装aerich包后，使用`aerich -h`命令查看使用说明。

> 如果以存在`./migrations` 目录和`pyproject.toml`中已有`[tool.aerich]`配置可以跳过此步骤。

`-t`参数用于指定在**2.1 模型设置**中设置的数据库配置，`--location`参数用来指定`migrations`目录的位置。本项目初始化使用的命令应为：

```shell
aerich init -t src.settings.DATABASE_CONFIG

# Output
Success create migrate location ./migrations
Success generate config file pyproject.toml
```

初始化后的`pyproject.toml`文件中关于aerich的内容如下：

```toml
# pyproject.toml
[tool.aerich]
tortoise_orm = "src.settings.DATABASE_CONFIG"
location = "./migrations"
src_folder = "./."
```

- tortoise_orm: 为`-t`参数指定配置参数对象。
- location: 迁移文件目录，相对于根目录。
- src_folder: 源文件的目录，相对于根目录（不需要修改）。

### 2.3 生成迁移文件

> 如果以初始化完成`./migrations`目录可以跳过此步骤。

###### 迁移默认数据库

使用如下命令生成模型的迁移文件：

```shell
aerich init-db

# Output
Success create app migrate location migrations\FastSample
Success generate schema for app "FastSample"
```

###### 迁移其他数据库

由于默认的迁移只迁移`default`数据库，如果其他附属数据库也需要迁移，需要用到`--app [appname]`来指定：

```shell
aerich --app FastDouble init

# Output
Success create app migrate location migrations\FastDouble
Success generate schema for app "FastDouble"
```

执行完成后会自动在数据库中生成对应的表。

### 2.4 模型的更新

> 如果`./migrations`目录下已存在更新用的sql文件并为最终版本，可以直接使用更新命令`aerich upgrade`进行更新。

###### 生成更新文件

当我们的模型发生变更后，要使用`aerich migrate`命令来生成更新的文件，例如将`password_hash`更新为`password`：

```python
class User(models.Model):
    # password_hash = fields.CharField(max_length=128)
    password = fields.CharField(max_length=128)
```

然后使用`aerich migrate`来迁移，`--name [filename]`可以指定更新的生成文件名，默认为`update`。

> `aerich migrate`命令也是仅对`default`的app进行检测，如果其他数据库也需要更新，要与之前**2.3 生成迁移文件**中所提到的一样，使用参数指定，例如：`aerich --app [appname] migrate`。后续的其他命令要对附属数据库操作需要用到同样的参数。

```shell
aerich migrate --name user

# Output
Rename password_hash to password? [True]:
Success migrate 1_20211126094013_user.sql
```

> 注意这里将`password_hash`列更名为`password`，出现了提示`Rename password_hash to password?`，默认为`True`，也可以输入`False`，区别如下：
>
> - True: 直接重命名列，生成一条sql语句。如果用到sql关键字为`RENAME`，需要MySQL8.0+才可以使用。
> - False：先删除列，然后在创建新列，使用到两条sql语句。
>
> 解决方法：
>
> 手动进入到生成的迁移文件中，修改SQL语句：
>
> ```sql
> -- 旧的 rename的sql语句
> ALTER TABLE `user_user` RENAME COLUMN `no_user` TO `user_number`;
> -- 修改为下面适配 5.7的 change语句
> ALTER TABLE `user_user` CHANGE COLUMN `no_user` `user_number` INT;
> ```
>
> 

###### 更新与降级

迁移文件生成后，我们可以根据需要使用`upgrade`与`downgrade`命令来对数据库的版本进行管理。

使用`aerich upgrade`命令将数据库更新到迁移文件所对应的最新版本。

```shell
aerich upgrade

# Output
Success upgrade 1_20211126094013_user.sql
```

使用`aerich downgrade`来降级版本。

```shell
aerich downgrade -h

# Output
Usage: aerich downgrade [OPTIONS]

  Downgrade to specified version.

Options:
  -v, --version INTEGER  Specified version, default to last.  [default: -1]

# ------------------------
aerich downgrade

# Output
Downgrade is dangerous, which maybe lose your data, are you sure? [y/N]: y
Success downgrade 1_20211126094013_user.sql
```

###### 查看更新与历史

`aerich history`查看数据库已经完成的迁移。

`aerich heads`显示需要迁移的内容。



## 3 预编译

项目使用cx_Freeze包进行编译打包，在激活python环境后使用`pip insall cx_Freeze`命令安装（会存在依赖文件，如果有`conda`环境建议使用`conda install -c conda-forge cx_freeze`安装）。

然后在项目根目录下使用`python setup.py build`命令进行编译。

> cx_Freeze打包时需要用到一些系统级别的工具包。
>
> Ubuntu系统需要额外使用`apt install patchelf`命令安装`patchelf`。
>
> 其他的依赖根据错误提示使用`apt`进行安装即可。
>
> 不使用`pip`而是使用`conda install -c conda-forge cx_freeze`安装它的话，只需要安装`patchelf`即可，不会有其他依赖报错。



## 4 打包镜像

### 4.1 打包编译镜像

1. 首先在项目目录中执行**3 预编译**的能力，编译完成后会生成`./build`目录。

2. 使用docker命令指定dockerfile文件进行镜像打包：

   ```shell
   docker build -t [tag] -f ./docker/build_dockerfile .
   ```

   - `-t`：指定镜像的tag
   - `-f`：指定dockerfile文件为**1.1 项目依赖文件**中提到的`build_dockerfile`文件。

   > 最后的`.`为`docker build`命令的`PATH`参数，指定当前目录为工作目录，不可省略。

### 4.2 打包源码镜像

1. 首先确定目录下是否有`./build`编译文件目录，有则删除，可以减小镜像大小。

2. 使用docker命令指定dockerfile文件进行镜像打包：

   ```shell
   docker build -t [tag] -f ./docker/python_dockerfile .
   ```

   各参数同**4.1 打包编译镜像**参数一致，只不过指定的dockerfile文件要变为`python_dockerfile`。

### 4.3 dockerfile文件说明

在**1.1 项目依赖文件**中提到，`docker`目录如下：

```
└── docker *
    ├── build_dockerfile
    └── python_dockerfile
```

其中`build_dockerfile`和`python_dockerfile`两个文件分别用于打包编译镜像与打包源码镜像。

###### build_dockerfile

`build_dockerfile`为用于打包编译镜像的dockerfile文件，内容如下：

```dockerfile
# 以 debian:buster-slim系统为基础镜像  buster代表debian10  slim代表最简镜像
FROM debian:buster-slim
# 修改 Linux默认的"LANG=C" 为 "UTF-8"，因为python默认编码为 utf-8
ENV LANG C.UTF-8
# 复制 Linux下的编译文件目录到 /MyProject目录下
COPY ./build/exe.linux-x86_64-3.8 /MyProject
# 设置镜像的工作目录为 /MyProject
WORKDIR /MyProject

# 配置apt源并安装vim
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y vim

# 指定docker镜像启动的默认执行命令
CMD ["./main"]
```

###### python_dockerfile

`python_dockerfile`为打包源码镜像的文件，与打包编译镜像不同，由于源码的运行需要python环境，所以打包源码镜像时要在镜像里初始化一个项目运行的python环境：

```dockerfile
# 以 python:3.8-slim-buster 镜像为基础环境，包含一个debian系统与 python 3.8.12 环境
FROM python:3.8-slim-buster
ENV LANG C.UTF-8
# 复制项目源码到 /MyProject目录，并设置工作目录
COPY . /MyProject
WORKDIR /MyProject
# 为 debian的 apt程序切换 aliyun的源， 然后安装vim
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y vim

#RUN pip install --no-cache-dir --upgrade pip setuptools -i https://mirrors.aliyun.com/pypi/simple/
# 安装 python的依赖包，安装完成后删除 ~/.cache目录，降低镜像大小
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ \
    && rm -rf ~/.cache

# 设置镜像启动命令，在shell中使用空格分割的命令，在dockerfile中应使用字符串数组进行表示
# 例如: "python main.py --name hello" -> ["python","main.py","--name","hello"]
CMD ["python","main.py"]
```

