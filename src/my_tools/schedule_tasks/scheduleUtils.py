# -*- coding: utf-8 -*-
# @Time    : 2022/3/7:11:09
# @Author  : fzx
# @Description : 定时任务

# import schedule_tasks
from .. import schedule_tasks

# 1.使用BlockingScheduler

scheduler = schedule_tasks.scheduler

# 将被装饰的task注册为按照置顶时间间隔进行
def times_every_secs(seconds):
    def make(func):
        scheduler.add_job(func, "interval", seconds=seconds)
        return func
    return make


# 将被装饰的task注册为按照每天固定时间进行
def timed_on_time(hours, minute):
    def make(func):
        scheduler.add_job(func, "cron", hours=hours, minute=minute)

        # 周期每年某些月某天某时执行
        scheduler.add_job(func, 'cron', month='1,4,7,10', day=1, hour=0, minute=0, second=0)
        return func
    return make


@times_every_secs(seconds=7200)   # 两小时执行一次
def demo():
    pass

# 2.使用 AsyncIOScheduler

async def func():
    print("hello!")