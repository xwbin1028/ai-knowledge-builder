from fastapi import APIRouter

address = APIRouter(prefix="/address", tags=["地址模块"])

@address.get("/info")
def address_info():
    pass

@address.get("/list")
def address_info():
    pass
