# -*- coding: utf-8 -*-
# @Time    : 2022/3/2:14:05
# @Author  : fzx
# @Description :

import typer


Application = typer.Typer()


@Application.command()
def run():
    import uvicorn
    from .settings import HTTP_API_LISTEN_HOST, HTTP_API_LISTEN_PORT
    from .faster import fast_app

    uvicorn.run(
        fast_app,
        host=HTTP_API_LISTEN_HOST,
        port=HTTP_API_LISTEN_PORT,
        reload=False,
    )


