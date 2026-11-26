from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, List

# 统一返回
T = TypeVar("T")
class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "success"
    data: Optional[T] = None

# 用户
class UserItem(BaseModel):
    id: int
    name: str
    age: int
    phone: str

class UserListData(BaseModel):
    total: int
    page: int
    size: int
    items: List[UserItem]

