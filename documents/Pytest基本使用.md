# 1 环境搭建

使用Pytest对FastAPI项目进行单元测试，其所有依赖如下，`pytest`包必装，其他按需安装：

```
pytest
# Pytest
pytest-cov
pytest-html
pytest-xdist
pytest-rerunfailures
pytest-ordering
pytest-asyncio

# FastAPI Testing
httpx
requests

# Other Tool
faker
```

## 1.1 Pytest测试依赖

- pytest: 基础
- pytest-cov: 用于生成测试覆盖率
- pytest-html: 用于生成html格式的测试报告
- pytest-xdist: 用于分布式执行测试用例(并行)
- pytest-rerunfailures: 用于测试用例失败重运行
- pytest-ordering: 用于调整测试用例的执行顺序
- pytest-asyncio: 异步运行的依赖

## 1.2 FastAPI测试依赖

- httpx: 异步的fastapi测试用客户端
- requests: 依赖

## 1.3 依赖

- faker: 用于生成一些假数据

# 2 项目结构

## 2.1 原始目录

以`device`项目为例，其原始项目结构如下:

```
device  // 其中带*为文件夹
丨--main.py
丨--manage.py
丨--libs *
丨--src *
   丨--__init__.py
   丨--settings.py
   丨--db *
      丨--database.py
      丨--models.py
   丨--routers *
      丨--__init__.py
      丨--object *
         丨--__init__.py
         丨--cu.py
         丨--object.py
         丨--subnet.py
丨--requirements.txt
```

## 2.2 单元测试目录

测试目录内部树形结构尽量与项目目录树形结构一致。

首先在`device`下新建`test`包，然后再在`test`下新建`unit`:

```
device
丨--test *
   丨--__init__.py
   丨--unit *
      丨--__init__.py
```

之后在`unit`下依次创建以`test_`开头的包或文件，覆盖需要测试目录：

```
丨--unit *
   丨--test_main.py 
   丨--test_src *
      丨--test_routers *
         丨--test_object *
            丨--test_cu.py
            丨--test_object.py
            丨--test_subnet.py
```

## 2.3 命名格式

Pytest执行时会自动检测指定目录或模块下符合**命名规则**的函数和类方法，并执行测试。Pytest检测的**命名规则**可以通过修改配置进行变更，默认的规则如下：

- 测试类以`Test`，且不能包含`__init__()`方法。
- 测试文件以`test_`开头。
- 测试函数和方法以`test_`开头。

> - 虽然Pytest对测试文件所在的python包没有严格的约束，但是建议与测试文件保持同一命名规则（`test_`开头，如果通过`python_files `修改过则应与修改后的规则一致）。
> - 测试时有些时候需要用到一些依赖module和函数，他们的命名规则并不受Pytest约束，为了方便管理，人为规定以`pytest_`开头命名这些依赖，例如：针对`routers`包的`session`级依赖，应该在`test_routers`包下新建`pytest_routers.py`文件。
> - 接口测试函数的名称中除了`test_`前缀名，剩余部分应该与所测接口函数名称一致，例如`get_subnets()`的测试函数应为`test_get_subnets()`。

# 3 测试代码

## 3.1 测试用客户端

### 3.1.1 TestClient

FastAPI提供`fastapi.testclient.TestClient`对象对其接口进行单元测试，下面介绍其基本使用方法。

使用FastAPI创建一个`get`接口：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_main():
    return {"msg": "Hello World"}
```

正常FastAPI实例的启动需要使用`uvicorn.run()`，但是通过`fastapi.testclient.TestClient`可以在不启动FastAPI服务的情况下对其进行单元测试：

```python
from fastapi.testclient import TestClient

from .main import app  # app:FastAPI 此app即为FastAPI的实例对象

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

### 3.1.2 异步客户端

FastAPI提供的`fastapi.testclient.TestClient`并不支持异步测试，如果需要进行异步测试，那么异步客户端就需要使用到`httpx`提供的`httpx.AsyncClient`，使用前应该先使用`pip install httpx`进行安装。

同样针对**3.1.1**中的`get`接口进行测试：

```python
import pytest
from httpx import AsyncClient

from .main import app


@pytest.mark.anyio
async def test_read_main():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

`@pytest.mark.anyio`装饰器标记该测试函数，以边Pytest知道该函数应该异步执行。

> `@pytest.mark.anyio`来自`anyio`库，如果使用的是`pytest-asyncio`库应该使用`@pytest.mark.asyncio`装饰器进行标记。

## 3.2 测试startup与shutdown

**2.1 原始目录**中可看到在项目根目录下有`main.py`文件：

```python
# main.py
app = FastAPI()

@app.on_event("startup")
async def startup() -> None:
    logger.debug(f"[FastAPI startup] - 连接数据库")
    database_ = app.state.database
    if not database_.is_connected:
        await database_.connect()
    Process()


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.debug(f"[FastAPI shutdown] - 断开数据库")
    database_ = app.state.database
    if database_.is_connected:
        await database_.disconnect()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=HTTP_API_PORT, debug=False)
```

此时想测试`startup`与`shutdown`的效果，首先根据**2.2 单元测试目录**与**2.3 命名格式**部分要求，我们需要将单元测试方法写在`./unit/test_main.py `文件内：

```python
# test_main.py
from fastapi.testclient import TestClient
from main import app

def test_startup_and_shutdown():
    # 首先获取测试客户端 
    with TestClient(app) as client:
        # 测试startup或shutdown需要先把FastAPI启动起来，所以随便发送一个请求来激活FastAPI
        _ = client.get("/object/subnet/all")
        # 检验startup中连接的数据库是否保持连接
        # 也可以通过上述请求的响应数据是否正常来进行判断，若数据库连接不正常，上述请求无法获取数据
        assert app.state.database.is_connected
    # 客户端关闭后FastAPI触发shutdown的Event
		# 检验shutdown后数据库连接是否正常关闭
    assert app.state.database.is_connected is False
```

## 3.3 编写接口的单元测试

以`subnet.py`内的`get_subnets`接口为例编写一个此接口的测试用例。

### 3.3.1 目录结构

`subnet.py`所处目录结构为：

```
device
丨--src *
   丨--routers *
      丨--object *
         丨--subnet.py
```

按照**2 项目结构**中所列要求，其对应测试文件`test_subnet.py`目录结构应为：

```
丨--unit *
   丨--test_src *
      丨--test_routers *
         丨--test_object *
            丨--test_subnet.py
```

### 3.3.2 测试函数

`get_subnets`接口代码如下：

```python
# subnet.py
subnet_router = APIRouter(prefix="/subnet", tags=["subnet"])

@subnet_router.get("/all", description="获取所有的子网")
async def get_subnets() -> Any:
    return await Subnet.objects.values()
```

根据命名要求编写如下测试函数：

```python
# test_subnet.py
from fastapi.testclient import TestClient  # FastAPI的测试客户端

from main import app

def test_get_subnets():
    with TestClient(app) as client:
        response = client.get("/object/subnet/all")
    assert response.status_code == 200
```

### 3.3.3 异步测试函数

将上述测试函数改造为一个异步函数，使得Pytest可以异步的执行多个测试函数，这样可以提升Pytest的测试效率，改造后的函数如下：

```python
# test_subnet.py
from httpx import AsyncClient  # httpx提供的异步测试客户端

from main import app

@pytest.mark.asyncio
async def test_get_subnets():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/object/subnet/all")
    assert response.status_code == 200
```

- `@pytest.mark.asyncio`装饰器：需要安装`pytest-asyncio`依赖，此装饰器用来向Pytest标明该测试函数应该异步执行。
- `AsyncClient`测试客户端：需要安装`httpx`依赖，异步的测试客户端。

**重点：**如果只修改为上述内容，运行Pytest测试命令测试是不通过的，`Failed`中的错误信息为`AssertionError: DatabaseBackend is not running` ，很显然这是没有连接数据库造成的，这是因为`AsyncClient`并不会执行FastAPI的`Event`，也就是说`@app.on_event("startup")`与`@app.on_event("shutdown")`所装饰的函数并没有执行，需要我们手动启动。所以修改上面的代码为：

```python
# test_subnet.py
from main import app, startup, shutdown

@pytest.mark.asyncio
async def test_get_subnets():
    await startup()
    async with AsyncClient(app=app, base_url="http://test") as client:
        # await startup() # 也可以将startup写在此处
        response = await client.get("/object/subnet/all")
    assert response.status_code == 200

    await shutdown()
```

这样一个异步的接口测试函数就写完了。

## 3.4 结构优化

按**3.3 编写接口的单元测试**部分介绍的内容，我们写好多个接口的测试函数后会发现这些测试函数内含有大量的重复代码片段：

```python
@pytest.mark.asyncio
async def test_pass():
    await startup()
    async with AsyncClient(app=app, base_url="http://test") as client:
        pass

    await shutdown()
```

即每个测试函数里都去创建客户端、连接数据库，会降低我们的测试运行效率，此时可以利用`@pytest.fixture(scope="session")`这个特性将客户端的创建、数据库的连接提取到`session`级，这样一个`session`级包下所有的测试函数都可以共用一个客户端，也避免了每执行一次测试函数都要重新连接数据库的问题。

首先确定好应将这些内容设置到哪个`session`中，因为我们在`./test_main.py`中已经测试了`startup`与`shutdown`的效果，所以后续测试都默认它们是执行成功的，所有接口都在`./src/routers/object`包下的`*.py`的文件中，所以我们从`src`、`routers`、`object`任选一级的`session`都可以，考虑到后续`routers`下会增加接口，所以本例选择在`src`级来完成异步测试客户端的创建于数据库的连接建立。

### 3.4.1 重复内容提取

根据**2 项目结构**中提到的规则，在`./test/unit/test_src/`目录下创建`pytest_src.py`文件，此时目录结构应该如下：

```
丨--unit *
   丨--test_main.py 
   丨--test_src *
      丨--pytest_src.py  
      丨--test_routers *
```

然后写入如下初始化内容：

```python
# pytest_src.py

@pytest.fixture(scope="session", autouse=True, name="fast_client")
async def pytest_start_async_fastapi():
    async with AsyncClient(app=app, base_url="http://test") as fast_client:
        await startup()
        yield fast_client

    await shutdown()
```

- `pytest_start_async_fastapi`：按照之前所约束的规则进行命名，由于此函数为依赖函数，所以`pytest_`开头，后续跟一个能表达函数作用的名称。
- `@pytest.fixture(scope="session")`：表明该函数的适用等级为`session`即python的包级，默认为`function`，另外还有`module`对应python的一个`.py`文件。
- `@pytest.fixture(autouse=True)`：`autouse=True`用于标明自动运行，否则只有在被使用到时该依赖函数才会被执行，这个参数可以根据需求自行选择。
- `@pytest.fixture(name="fast_client")`：`name="fast_client"`用于标明使用时的别名，`pytest_start_async_fastapi`使用时名称太长不宜用，使用`fast_client`这个别名。
- `yield fast_client`：上下分的分界线，`yield`上面的内容为初始化时执行，`yield`下面的内容即为该函数所标级别内所有测试方法都执行完成后要执行的内容。`yield`关键字后跟的就是暴露给测试函数使用的内容。

### 3.4.2 修改测试函数

将测试客户端的创建提取到`session`级后，也需要修改所有的测试函数，其内部不需要再进行客户端的创建工作了。

以修改`test_get_subnets()`函数为例：

```python
# 导入session级的依赖函数
from test.unit.test_src.pytest_src import pytest_start_async_fastapi

@pytest.mark.asyncio
async def test_get_subnets(fast_client: AsyncClient):
    response = await fast_client.get("/object/subnet/all")
    assert response.status_code == 200
```

- `fast_client: AsyncClient`参数：通过函数名称`pytest_start_async_fastapi`导入依赖，在所有需要用到测试客户端的测试函数的参数列表中添加该函数名称，即可使用`pytest_start_async_fastapi`这个依赖函数通过`yield`关键字暴露的内容。在之前我们通过`name="fast_client"`为其设置了别名，所以参数列表中也可以使用此别名，和直接使用函数名称是一个效果。

# 4 启动测试

Pytest启动方式有多种，可以通过命令行激活python环境后的`pytest`命令来运行测试，也可以通过在运行`*.py`启动。

## 4.1 启动

在项目根目录下创建`./pytest_run.py`文件（也可以是其他，根据具体情况定制），写入如下内容：

```python
# pytest_run.py
import pytest

test_result = pytest.main()
print(f"[Pytest result] - {test_result}")
```

移动到项目根目录，使用`python pytest_run.py`即可运行测试，Pytest会自动扫描根目录下复合命名规则的测试函数及其依赖并运行测试，生成测试报告。

## 4.2 配置

关于测试报告的生成位置、报告名称、覆盖率报告的位置和名称、扫描目录等等内容都可以通过修改Pytest的配置来达到变更需要，可以通过`pytest.ini`文件、命令行传参、`main()`函数传参等多种方式实现修改Pytest的配置。

在**4.1 启动**中使用`.py`文件的形式启动Pytest，可以通过代码的方式设置各种目录及名称，所以更推荐使用这种方式启动Pytest。

修改内容如下：

```python
def run_test():
    import pytest
    from pathlib import Path
    project_dir = Path(__file__).parent

    test_result = pytest.main([
        str(project_dir.joinpath('test')),
        f"--html={str(project_dir.joinpath('test_report/report.html'))}",
        f"--cov={str(project_dir.joinpath('src'))}",
        f"--cov-report=html:{str(project_dir.joinpath('test_report/cov_html'))}",
    ])
    print(f"[Pytest result] - {test_result}")
    
if __name__ == "__main__":
    run_test()
```

- `str(project_dir.joinpath('test'))`：所有参数都以字符串的形式传递，`pytest.main()`参数为一个`List`，每一个元素代表一个参数位置，第一个位置`str(project_dir.joinpath('test'))`代表测试文件所在位置，指定`./test`目录，避免扫描根目录有全局污染。
- `f"--html={str(project_dir.joinpath('test_report/report.html'))}"`：指定生成html形式的测试报告，文件位置为`./test_report/report.html`。
- `f"--cov={str(project_dir.joinpath('src'))}"`：指定要计算覆盖率的目录，本项目只需要计算`./src`目录下的覆盖率即可。
- `f"--cov-report=html:{str(project_dir.joinpath('test_report/cov_html'))}"`：指定覆盖率报告的形式和位置。

# 5 总结

至此，编写完所有的测试函数，并对其结构进行了整理优化，使其更易读。

一个完整的FastAPI的项目的测试代码目录如下（device项目为例）：

```
device // 以下目录省略python包的__init__.py文件
丨--main.py
丨--manage.py
丨--libs *
丨--src *
   丨--settings.py
   丨--db *
      丨--database.py
      丨--models.py
   丨--routers *
      丨--object *
         丨--cu.py
         丨--object.py
         丨--subnet.py
丨--test *
   丨--unit *
      丨--test_main.py 
      丨--test_src *
         丨--pytest_src.py 
         丨--test_routers *
            丨--test_object *
               丨--test_cu.py
               丨--test_object.py
               丨--test_subnet.py
丨--test_report *
丨--requirements.txt
```

