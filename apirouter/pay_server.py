from fastapi import APIRouter

pay = APIRouter(prefix="/pay", tags=["支付模块"])


@pay.get("/add")
def pay_add():
    pass

@pay.get("/remove")
def pay_remove():
    pass

@pay.get("/detail")
def pay_detail():
    pass