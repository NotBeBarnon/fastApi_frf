## 1.2.5-sample (2023-02-21)

### Feat

- 增加kafka连接
- 增加redis哨兵模式连接

## 1.2.4-sample (2023-02-17)

### Fix

- 增加异步定时任务

## 1.2.3-sample (2022-02-16)

### Fix

- 添加FastAPI自动生成基础方法

## 1.2.2-sample (2022-02-14)

### Fix

- 补充例子
- 修改toml文件中关于database的配置

## 1.2.1-sample (2022-02-14)

### Fix

- 修复预编译时忽略pyproject.toml的问题
- 修改配置从toml中提取
- 修复setup.py中不能自动适配version的问题

## 1.2.0-sample (2022-02-14)

### Fix

- 新增settings中读取toml项目配置
- 添加例子

### Feat

- 添加单元测试目录结构

## 1.1.1-sample (2021-12-16)

### Fix

- 变更version配置
- 删除toml包

### Refactor

- 变更settings文件的编码格式

## 1.1.0-sample (2021-12-16)

### Refactor

- FastAPI文档自动适配version

### Feat

- 添加version配置，添加工具包

## 1.0.0-sample (2021-12-15)

### Fix

- 修改字段验证器错误提示
- 重构项目结构
- 添加Linux系统下打包uvloop
- 修复部分写法问题
- 更改项目结构
- 完善CBV调度
- 修改ShortUIDField
- 添加序列化示例代码
- 修复setup打包时site-packages扫描不全的问题
- 修复site-packages在Linux下不能正确匹配的问题
- 修复FastAPI缺少依赖的问题

### Refactor

- 修改tag规则
- 修改all参数，添加uvloop依赖

### Perf

- 响应使用orjson

### Feat

- 添加FastAPI的CBV实现
- 添加数据库迁移能力
- 搭建数据库连接与setup编译框架
- FastAPI基本架构
- Init
