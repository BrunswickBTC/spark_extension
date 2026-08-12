import asyncio

from fastapi import APIRouter
from lnbits.db import Database


db = Database("ext_sparkl2")

from .views import sparkl2_generic_router
from .views_api import sparkl2_api_router

sparkl2_ext = APIRouter(prefix="/sparkl2", tags=["Spark L2"])
sparkl2_ext.include_router(sparkl2_generic_router)
sparkl2_ext.include_router(sparkl2_api_router)
sparkl2_static_files = [{"path": "/sparkl2/static", "name": "sparkl2_static"}]
scheduled_tasks: list[asyncio.Task] = []


def sparkl2_start():
    from lnbits.tasks import create_permanent_unique_task
    from .reconciler import deposit_reconciliation_task

    scheduled_tasks.append(
        create_permanent_unique_task(
            "ext_sparkl2_deposit_reconciliation", deposit_reconciliation_task
        )
    )


def sparkl2_stop():
    for task in scheduled_tasks:
        task.cancel()


__all__ = [
    "db",
    "sparkl2_ext",
    "sparkl2_static_files",
    "sparkl2_start",
    "sparkl2_stop",
]
