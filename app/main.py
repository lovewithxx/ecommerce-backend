r"""
应用入口。

启动：
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

文档：
    http://127.0.0.1:8000/docs

=====================================================================
【为什么必须从项目根目录启动，用 app.main:app 这种写法】
=====================================================================
你原来的代码里写的是 `from models.users import User`、`from crud import users`，
这种导入假设 `app/` 目录本身在 sys.path 里。

后果：
    从项目根启动 `uvicorn app.main:app` -> ModuleNotFoundError: No module named 'models'
    必须 cd 进 app/ 才能跑 -> 但那样 .env 又找不到了

本项目的写法把所有导入都改成 `from app.xxx import yyy`，
所以：从项目根启动，一切正常。记住这个约定，后面所有文件都这么写。
=====================================================================
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config.app_conf import settings
from app.config.db_conf import async_engine
from app.routers import cart as cart_router
from app.routers import category as category_router
from app.routers import favorite as favorite_router
from app.routers import product as product_router
from app.routers import user as user_router
from app.untils.exception import register_exception_handlers
from app.untils.response import success_response

# 前端页面目录（web/index.html）
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# 日志格式：时间 | 级别 | 模块 | 内容
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ec_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(
            "数据库连接成功：%s@%s:%s/%s",
            settings.db_user, settings.db_host, settings.db_port, settings.db_name,
        )
    except Exception as exc:                                   # noqa: BLE001
        logger.error("数据库连接失败：%s", exc)
        logger.error("请检查 .env 里的 DB_* 配置，以及 MySQL 服务是否启动")

    logger.info("服务已启动，文档地址 http://127.0.0.1:8000/docs")
    yield
    # 关闭时释放连接池，避免 MySQL 里留下一堆 sleep 连接
    await async_engine.dispose()
    logger.info("服务已关闭，连接池已释放")


app = FastAPI(
    title="电商平台 API",
    version="0.1.0",
    description="FastAPI + MySQL 电商系统。第一阶段：用户 / 商品 / 收藏 / 购物车 / 订单",
    lifespan=lifespan,
)

#异常处理器必须在挂路由之前注册 
register_exception_handlers(app)

# 挂载路由
app.include_router(user_router.router)
app.include_router(favorite_router.router)
app.include_router(cart_router.router)
app.include_router(category_router.router)
app.include_router(product_router.router)

# 商品图片静态目录
# 图片是 tools/fetch_images.py 提前下到本地的，所以前端显示图片不依赖外网。
# 访问 /images/phone/01.jpg 就是读 web/images/phone/01.jpg
IMAGES_DIR = WEB_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")

# 跨域配置
# 本项目认证走 Cookie，所以：
#   1. allow_credentials=True 必须为 True，否则浏览器不会保存/携带 Cookie
#   2. allow_origins 不能写 "*"，必须列出具体来源（浏览器规范禁止两者同时用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["系统"], summary="健康检查")
async def health():
    """
    健康检查。这个接口的价值：
        1. 确认服务活着
        2. 确认数据库连得上
        3. 确认表建出来了

    写代码时养成先看它的习惯 —— 出问题第一步就是确认这三件事。
    """
    db_status = "disconnected"
    tables: list[str] = []

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            result = await conn.execute(
                text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = :db ORDER BY TABLE_NAME"
                ),
                {"db": settings.db_name},
            )
            tables = [row[0] for row in result]
        db_status = "connected"
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("健康检查：数据库不可用（%s）", exc)

    return success_response(
        message="success",
        data={
            "status": "ok" if db_status == "connected" else "degraded",
            "db": db_status,
            "database": settings.db_name,
            "tables": tables,
            "version": "0.1.0",
        },
    )


@app.get("/", include_in_schema=False)
async def index():
    """
    返回前端页面。

    前端是单个 HTML 文件（web/index.html），不需要 npm、不需要打包，
    直接由 FastAPI 托管。和接口同源，所以不存在跨域问题。
    """
    page = WEB_DIR / "index.html"
    if not page.exists():
        return success_response(
            message="前端文件缺失",
            data={"expected": str(page), "docs": "/docs", "health": "/api/health"},
        )
    return FileResponse(page)


@app.get("/api", include_in_schema=False)
async def api_root():
    """给纯接口调用者一个入口提示。"""
    return success_response(
        message="服务已启动",
        data={
            "docs": "/docs",
            "health": "/api/health",
            "web": "/",
            "endpoints": [
                "POST /api/user/register",
                "POST /api/user/login",
                "POST /api/user/logout",
                "GET  /api/user/info",
                "PUT  /api/user/info",
                "PUT  /api/user/password",
            ],
        },
    )
