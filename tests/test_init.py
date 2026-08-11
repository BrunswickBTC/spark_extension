from fastapi import APIRouter

from .. import sparkl2_ext


def test_router():
    router = APIRouter()
    router.include_router(sparkl2_ext)
