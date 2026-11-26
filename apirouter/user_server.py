from fastapi import APIRouter
from apirouter.constants import UserItem, UserListData, ApiResponse

user = APIRouter(prefix="/user", tags=["用户模块"])


@user.get("/list")
def user_list():
    user_item = UserItem(id=1, name="张三", age=20, phone="13800138000")
    user_list_data = UserListData(total=120, page=1, size=10, items=[user_item])
    resp = ApiResponse(data=user_list_data)
    return resp


@user.get("/{user_id}")
def user_show(user_id: int):
    user_item = UserItem(id=user_id, name="张三", age=20, phone="13800138000")
    resp = ApiResponse(data=user_item)
    return resp


@user.delete("/{user_id}")
def user_remove(user_id: int):
    resp = ApiResponse(data=None)
    return resp


@user.post("")
def user_add(user_item: UserItem):
    resp = ApiResponse(data=user_item)
    return resp


@user.put("/{user_id}")
def user_edit(user_id: int, name: str | None, age: int | None, phone: str | None):
    user_item = UserItem(id=user_id, name=name, age=age, phone=phone)
    resp = ApiResponse(data=user_item)
    return resp

