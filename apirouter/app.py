from fastapi import FastAPI
from address_server import address
from pay_server import pay
from user_server import user
from other_server import other

app = FastAPI(
    description="练习给函数设置访问地址",
    swagger_ui_parameters={
        "swagger_js_url": "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.12.0/swagger-ui-bundle.js",
        "swagger_css_url": "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.12.0/swagger-ui.css",
        "swagger_favicon_url": "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.12.0/favicon-32x32.png",
    }
)

app.include_router(address)
app.include_router(pay)
app.include_router(user)
app.include_router(other)