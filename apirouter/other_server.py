import time

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
from mimetypes import guess_type
from fastapi import BackgroundTasks

PROJECT_ROOT = Path(__file__).resolve().parent.parent
print(PROJECT_ROOT)

other = APIRouter(prefix="/other", tags=["测试模块"])


@other.get("/user")
def other_user(keyword: str, size: int = 10, page: int = 1):
    print(f"{keyword} - {size} - {page}")
    return {
        "code": 0
    }


@other.delete("/student/{sid}")
def other_student(sid: int):
    print(f"删除id为{sid}的用户信息")
    return {
        "code": 0
    }


class Person(BaseModel):
    name: str
    age: int


@other.post("/add/person")
def add_person(person: Person):
    print(person)
    return {
        "message": person
    }


@other.post("/add/image")
async def add_image(account: str, image: UploadFile):
    print(f"基础信息account:{account},图片名:{image.filename},图片类型:{image.content_type}")

    file_data = await image.read()
    file_path: Path = PROJECT_ROOT / 'apirouter' / 'images' / image.filename
    print(file_path)
    file_path.write_bytes(file_data)

    return {
        "message": "上传成功",
        "account": account
    }


class Address(BaseModel):
    city: str
    detail: str

class User(BaseModel):
    id: int
    name: str
    age: int
    address: Address

@other.get("/search/{uid}")
def search_user(uid: int):
    address = Address(city="深圳", detail="宝安区")
    user = User(id=uid, name="张大帅", age=30, address=address)
    return user


@other.get("/getfile")
def get_file():
    file_path: Path = PROJECT_ROOT / 'apirouter' / 'images' / '74F2884AC65BA14F8E819CB0DD209B13.png'

    return FileResponse(
        # filename下载头标识,添加了filename自动添加下载头!无论浏览器能否打开
        # 都会变成下载!content-disposition:attachment;filename=文件名
        # filename="",
        path=file_path,
        media_type=guess_type(file_path.name)[0]
    )


def run_time(session_id: str):
    print("参数是：",session_id)
    print("这是一个耗时的方法")
    time.sleep(100)
    print("方法结束")


@other.get("/longtime")
def long_time(task: BackgroundTasks):
    print("开异步调用执行耗时的方法")
    task.add_task(run_time, session_id="001")
    print("请求并响应结果")
    return {
        "code": 0
    }
