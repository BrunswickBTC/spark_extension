from fastapi import APIRouter

from lnbits.db import Database

db = Database("ext_sparkl2")

from .views import sparkl2_generic_router
from .views_api import sparkl2_api_router
sparkl2_ext = APIRouter(prefix="/sparkl2", tags=["Spark L2"])
sparkl2_ext.include_router(sparkl2_generic_router)
sparkl2_ext.include_router(sparkl2_api_router)

sparkl2_static_files = [{"path": "/sparkl2/static", "name": "sparkl2_static"}]

__all__ = ["db", "sparkl2_ext", "sparkl2_static_files"]
