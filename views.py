from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

sparkl2_generic_router = APIRouter()


def sparkl2_renderer():
    return template_renderer(["sparkl2/templates"])


@sparkl2_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return sparkl2_renderer().TemplateResponse(
        "sparkl2/index.html", {"request": request, "user": user.json()}
    )
